from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.models import (
    ColumnSchema,
    ColumnType,
    DecimalParams,
    ImportRisk,
    RiskCategory,
    RiskExample,
    Severity,
)
from app.services.convert import convert_value

_LEADING_ZERO_INT = re.compile(r"^[+-]?0\d+$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_DECIMAL_RE = re.compile(r"^[+-]?\d+\.\d+$")


def scan_table(
    headers: list[str],
    rows: list[list[str]],
    columns: list[ColumnSchema],
    preview_limit: int = 50,
) -> list[ImportRisk]:
    risks: list[ImportRisk] = []
    scanned = len(rows)
    col_by_name = {c.name: c for c in columns}

    for idx, header in enumerate(headers):
        col = col_by_name.get(header) or ColumnSchema(name=header, type=ColumnType.STRING)
        values = [r[idx] if idx < len(r) else "" for r in rows]
        risks.extend(_scan_column(header, values, col, scanned, preview_limit))

    return _sort_risks(risks)


def _scan_column(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    out: list[ImportRisk] = []

    if col.type in {ColumnType.INTEGER, ColumnType.BIGINT, ColumnType.DOUBLE, ColumnType.DECIMAL}:
        out.extend(_leading_zero_risks(name, values, col, scanned, preview_limit))
        out.extend(_collision_risks(name, values, col, scanned, preview_limit))

    if col.type == ColumnType.DOUBLE:
        out.extend(_double_precision_risks(name, values, col, scanned, preview_limit))
        out.extend(_large_int_via_double(name, values, col, scanned, preview_limit))

    if col.type == ColumnType.DECIMAL:
        out.extend(_decimal_scale_risks(name, values, col, scanned, preview_limit))

    if col.type == ColumnType.DATE:
        out.extend(_null_conversion_risks(name, values, col, scanned, preview_limit, RiskCategory.INVALID_DATE, "Invalid dates become null"))

    if col.type == ColumnType.TIMESTAMP:
        out.extend(_timestamp_risks(name, values, col, scanned, preview_limit))

    if col.type in {
        ColumnType.INTEGER,
        ColumnType.BIGINT,
        ColumnType.DOUBLE,
        ColumnType.DECIMAL,
        ColumnType.BOOLEAN,
    }:
        # Generic null-after-conversion for non-empty that fail
        already = {(r.category, r.column) for r in out}
        generic = _null_conversion_risks(
            name, values, col, scanned, preview_limit, RiskCategory.NULL_AFTER_CONVERSION, "Values become null"
        )
        for g in generic:
            # Avoid duplicating date/timestamp specific cards
            if (RiskCategory.INVALID_DATE, name) in already or (RiskCategory.INVALID_TIMESTAMP, name) in already:
                continue
            # Skip if already covered by leading zero / scale cards for same examples? Keep distinct.
            if g.category == RiskCategory.NULL_AFTER_CONVERSION and col.type in {
                ColumnType.INTEGER,
                ColumnType.BIGINT,
            }:
                # leading-zero path converts successfully to int, not null
                pass
            out.append(g)

    # Deduplicate by risk_id
    dedup: dict[str, ImportRisk] = {}
    for r in out:
        dedup[r.risk_id] = r
    return list(dedup.values())


def _examples_from(
    indices: list[int],
    values: list[str],
    converted_map: dict[int, Optional[str]],
    preview_limit: int,
    reason: str,
    limit: int = 5,
) -> tuple[list[RiskExample], int]:
    examples: list[RiskExample] = []
    outside = 0
    for i in indices:
        outside_preview = (i + 1) > preview_limit
        if outside_preview:
            outside += 1
        if len(examples) < limit:
            examples.append(
                RiskExample(
                    row=i + 1,
                    original=values[i],
                    converted=converted_map.get(i),
                    reason=reason,
                    outside_preview=outside_preview,
                )
            )
    return examples, outside


def _leading_zero_risks(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    hits: list[int] = []
    converted_map: dict[int, Optional[str]] = {}
    for i, raw in enumerate(values):
        if not raw or not raw.strip():
            continue
        if not _LEADING_ZERO_INT.match(raw.strip()):
            continue
        converted = convert_value(raw, col)
        if converted is None:
            continue
        # Leading zeros lost when stored as number
        raw_digits = raw.strip().lstrip("+-")
        conv_digits = converted.lstrip("+-")
        if raw_digits.startswith("0") and raw_digits != conv_digits:
            hits.append(i)
            converted_map[i] = converted
    if not hits:
        return []
    examples, outside = _examples_from(
        hits, values, converted_map, preview_limit, "Leading zeros removed by numeric conversion"
    )
    return [
        ImportRisk(
            risk_id=f"{name}-leading-zero",
            column=name,
            category=RiskCategory.LEADING_ZERO_LOSS,
            severity=Severity.HIGH,
            affected_rows=len(hits),
            scanned_rows=scanned,
            examples=examples,
            explanation=(
                f"Removing leading zeros from {name} can break matches with the same identifier in another table."
            ),
            recommended_type=ColumnType.STRING,
            recommended_action="Keep as String",
            outside_preview_count=outside,
            title=f"{_pretty(name)} will lose leading zeros",
        )
    ]


def _collision_risks(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    buckets: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for i, raw in enumerate(values):
        if not raw or not raw.strip():
            continue
        converted = convert_value(raw, col)
        if converted is None:
            continue
        buckets[converted].append((i, raw))

    collision_indices: list[int] = []
    converted_map: dict[int, Optional[str]] = {}
    for converted, group in buckets.items():
        originals = {raw for _, raw in group}
        if len(originals) > 1:
            for i, raw in group:
                collision_indices.append(i)
                converted_map[i] = converted

    if not collision_indices:
        return []
    # unique preserve order
    seen: set[int] = set()
    ordered = []
    for i in collision_indices:
        if i not in seen:
            seen.add(i)
            ordered.append(i)

    examples, outside = _examples_from(
        ordered, values, converted_map, preview_limit, "Distinct source values map to the same stored value"
    )
    return [
        ImportRisk(
            risk_id=f"{name}-identifier-collision",
            column=name,
            category=RiskCategory.IDENTIFIER_COLLISION,
            severity=Severity.HIGH,
            affected_rows=len(ordered),
            scanned_rows=scanned,
            examples=examples,
            explanation=(
                f"Different source values in {name} become the same stored value after conversion, which can merge distinct records."
            ),
            recommended_type=ColumnType.STRING,
            recommended_action="Keep as String",
            outside_preview_count=outside,
            title=f"{_pretty(name)} values will collide",
        )
    ]


def _double_precision_risks(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    hits: list[int] = []
    converted_map: dict[int, Optional[str]] = {}
    for i, raw in enumerate(values):
        if not raw or not raw.strip():
            continue
        cleaned = raw.strip().replace(",", "")
        if not _DECIMAL_RE.match(cleaned) and not _INT_RE.match(cleaned):
            continue
        # Long fraction or huge int that float cannot preserve
        if "." in cleaned and len(cleaned.split(".", 1)[1]) > 15:
            converted = convert_value(raw, col)
            if converted is not None and not _same_numeric_meaning(cleaned, converted):
                hits.append(i)
                converted_map[i] = converted
            elif converted is not None:
                # Still check float drift
                try:
                    if Decimal(cleaned) != Decimal(converted):
                        hits.append(i)
                        converted_map[i] = converted
                except InvalidOperation:
                    pass
        elif _INT_RE.match(cleaned) and len(cleaned.lstrip("+-")) > 15:
            converted = convert_value(raw, col)
            if converted is not None and cleaned.lstrip("+") != converted.lstrip("+"):
                hits.append(i)
                converted_map[i] = converted
        else:
            converted = convert_value(raw, col)
            if converted is None:
                continue
            if not _same_numeric_meaning(cleaned, converted):
                hits.append(i)
                converted_map[i] = converted

    if not hits:
        return []
    examples, outside = _examples_from(
        hits, values, converted_map, preview_limit, "Double cannot preserve exact digits"
    )
    return [
        ImportRisk(
            risk_id=f"{name}-decimal-precision-loss",
            column=name,
            category=RiskCategory.DECIMAL_PRECISION_LOSS,
            severity=Severity.MEDIUM,
            affected_rows=len(hits),
            scanned_rows=scanned,
            examples=examples,
            explanation=f"Storing {name} as Double may round digits and change totals or measurements.",
            recommended_type=ColumnType.DECIMAL,
            recommended_action="Use Decimal with enough scale",
            recommended_decimal=DecimalParams(precision=38, scale=18),
            outside_preview_count=outside,
            title=f"{_pretty(name)} may lose precision",
        )
    ]


def _large_int_via_double(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    # Covered largely by precision; keep empty to avoid noise
    return []


def _decimal_scale_risks(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    params = col.decimal or DecimalParams()
    hits: list[int] = []
    converted_map: dict[int, Optional[str]] = {}
    for i, raw in enumerate(values):
        if not raw or not raw.strip():
            continue
        cleaned = raw.strip().replace(",", "")
        if cleaned.startswith("$"):
            continue
        if not (_DECIMAL_RE.match(cleaned) or _INT_RE.match(cleaned)):
            continue
        converted = convert_value(raw, col)
        if converted is None:
            continue
        if not _same_numeric_meaning(cleaned, converted):
            hits.append(i)
            converted_map[i] = converted
    if not hits:
        return []
    scale = max(2, params.scale if params.scale > 0 else 2)
    examples, outside = _examples_from(
        hits, values, converted_map, preview_limit, f"Rounded under decimal({params.precision},{params.scale})"
    )
    return [
        ImportRisk(
            risk_id=f"{name}-decimal-scale-rounding",
            column=name,
            category=RiskCategory.DECIMAL_SCALE_ROUNDING,
            severity=Severity.HIGH,
            affected_rows=len(hits),
            scanned_rows=scanned,
            examples=examples,
            explanation=(
                f"Values in {name} are rounded under decimal({params.precision},{params.scale}), which can change financial totals."
            ),
            recommended_type=ColumnType.DECIMAL,
            recommended_action=f"Use decimal({params.precision},{scale})",
            recommended_decimal=DecimalParams(precision=max(params.precision, 10), scale=scale),
            outside_preview_count=outside,
            title=f"{_pretty(name)} will be rounded",
        )
    ]


def _null_conversion_risks(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
    category: RiskCategory,
    title_prefix: str,
) -> list[ImportRisk]:
    hits: list[int] = []
    converted_map: dict[int, Optional[str]] = {}
    for i, raw in enumerate(values):
        if raw is None or str(raw).strip() == "":
            continue
        converted = convert_value(raw, col)
        if converted is None:
            hits.append(i)
            converted_map[i] = None
    if not hits:
        return []
    examples, outside = _examples_from(
        hits, values, converted_map, preview_limit, "Non-empty source becomes null under proposed type"
    )
    rec_type = ColumnType.STRING
    return [
        ImportRisk(
            risk_id=f"{name}-{category.value}",
            column=name,
            category=category,
            severity=Severity.HIGH if category in {RiskCategory.INVALID_DATE, RiskCategory.INVALID_TIMESTAMP} else Severity.MEDIUM,
            affected_rows=len(hits),
            scanned_rows=scanned,
            examples=examples,
            explanation=(
                f"Non-empty values in {name} become null under {col.type.value}, which can drop rows from time-based or filtered analysis."
            ),
            recommended_type=rec_type,
            recommended_action="Keep as String",
            outside_preview_count=outside,
            title=f"{title_prefix} in {_pretty(name)}",
        )
    ]


def _timestamp_risks(
    name: str,
    values: list[str],
    col: ColumnSchema,
    scanned: int,
    preview_limit: int,
) -> list[ImportRisk]:
    # Identifier-like values inferred as timestamp
    id_hits: list[int] = []
    converted_map: dict[int, Optional[str]] = {}
    null_hits: list[int] = []
    for i, raw in enumerate(values):
        if not raw or not raw.strip():
            continue
        stripped = raw.strip()
        converted = convert_value(raw, col)
        if _INT_RE.match(stripped) and len(stripped) >= 4:
            id_hits.append(i)
            converted_map[i] = converted
        elif converted is None:
            null_hits.append(i)
            converted_map[i] = None

    risks: list[ImportRisk] = []
    if id_hits:
        examples, outside = _examples_from(
            id_hits,
            values,
            converted_map,
            preview_limit,
            "Identifier inferred as timestamp",
        )
        risks.append(
            ImportRisk(
                risk_id=f"{name}-invalid-timestamp",
                column=name,
                category=RiskCategory.INVALID_TIMESTAMP,
                severity=Severity.HIGH,
                affected_rows=len(id_hits),
                scanned_rows=scanned,
                examples=examples,
                explanation=(
                    f"Identifier-like values in {name} are being inferred as timestamps "
                    f"(for example 000123 → 0123-01-01T00:00:00.000Z)."
                ),
                recommended_type=ColumnType.STRING,
                recommended_action="Turn off timestamp inference.",
                outside_preview_count=outside,
                title=f"{_pretty(name)} misread as timestamp",
            )
        )
    if null_hits:
        risks.extend(
            _null_conversion_risks(
                name, values, col, scanned, preview_limit, RiskCategory.INVALID_TIMESTAMP, "Invalid timestamps become null"
            )
        )
    return risks


def _same_numeric_meaning(original: str, converted: str) -> bool:
    try:
        return Decimal(original) == Decimal(converted)
    except InvalidOperation:
        return original == converted


def _pretty(name: str) -> str:
    return name.replace("_", " ")


def _sort_risks(risks: list[ImportRisk]) -> list[ImportRisk]:
    order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    return sorted(risks, key=lambda r: (order[r.severity], r.column, r.risk_id))


def confidence_status(unresolved: int, resolved: int) -> str:
    if unresolved == 0 and resolved == 0:
        return "Ready to create table"
    if unresolved == 0 and resolved > 0:
        return "Important values preserved"
    if resolved > 0:
        return f"{resolved} of {resolved + unresolved} risks fixed"
    return f"{unresolved} import risks found"


def apply_recommended_fix(columns: list[ColumnSchema], risk: ImportRisk) -> list[ColumnSchema]:
    updated: list[ColumnSchema] = []
    for col in columns:
        if col.name != risk.column:
            updated.append(col)
            continue
        new_col = col.model_copy(deep=True)
        new_col.type = risk.recommended_type
        if risk.recommended_decimal is not None:
            new_col.decimal = risk.recommended_decimal
        elif risk.recommended_type != ColumnType.DECIMAL:
            new_col.decimal = None
        updated.append(new_col)
    return updated
