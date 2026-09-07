from __future__ import annotations

import re
from datetime import datetime

from app.models import ColumnSchema, ColumnType, DecimalParams

_INT_RE = re.compile(r"^[+-]?\d+$")
_DECIMAL_RE = re.compile(r"^[+-]?\d+\.\d+$")
_BOOL_RE = re.compile(r"^(true|false|yes|no|0|1)$", re.I)
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_US_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_TS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"
)


def _nonempty(values: list[str]) -> list[str]:
    return [v for v in values if v is not None and str(v).strip() != ""]


def infer_columns(headers: list[str], rows: list[list[str]]) -> list[ColumnSchema]:
    columns: list[ColumnSchema] = []
    for idx, name in enumerate(headers):
        col_vals = [r[idx] if idx < len(r) else "" for r in rows]
        columns.append(_infer_one(name, col_vals))
    return columns


def _infer_one(name: str, values: list[str]) -> ColumnSchema:
    samples = _nonempty(values)
    if not samples:
        return ColumnSchema(name=name, type=ColumnType.STRING)

    lower_name = name.lower()
    # Prefer identifier-like columns with leading zeros as numeric if all digits —
    # that mirrors Databricks over-eager inference (the risk we detect).
    if all(_INT_RE.match(v.strip()) for v in samples):
        max_abs = max(abs(int(v.strip())) for v in samples)
        # Leading-zero ids still look like integers to naive inference
        if max_abs > 2**31 - 1:
            return ColumnSchema(name=name, type=ColumnType.BIGINT)
        return ColumnSchema(name=name, type=ColumnType.INTEGER)

    if all(_looks_decimal(v) for v in samples):
        # Prefer double for mixed precision decimals (Databricks-like)
        scales = [_fraction_len(v) for v in samples]
        if max(scales) > 6:
            return ColumnSchema(name=name, type=ColumnType.DOUBLE)
        return ColumnSchema(
            name=name,
            type=ColumnType.DECIMAL,
            decimal=DecimalParams(precision=10, scale=0),  # aggressive default to demo risk
        )

    if all(_ISO_DATE.match(v.strip()) or _US_DATE.match(v.strip()) for v in samples):
        return ColumnSchema(name=name, type=ColumnType.DATE)

    if all(_TS_RE.match(v.strip()) for v in samples):
        return ColumnSchema(name=name, type=ColumnType.TIMESTAMP)

    # Mixed: if majority parse as date, infer date (invalids become null risks)
    dateish = sum(1 for v in samples if _ISO_DATE.match(v.strip()) or _US_DATE.match(v.strip()))
    if dateish >= max(1, len(samples) // 2) and ("date" in lower_name or dateish == len(samples)):
        return ColumnSchema(name=name, type=ColumnType.DATE)

    if "date" in lower_name and dateish > 0:
        return ColumnSchema(name=name, type=ColumnType.DATE)

    # Amount-like columns with currency/unknown stay string unless clean decimals
    if all(_BOOL_RE.match(v.strip()) for v in samples):
        return ColumnSchema(name=name, type=ColumnType.BOOLEAN)

    # Numeric-looking majority with some junk → double/decimal with nulls
    numericish = sum(1 for v in samples if _INT_RE.match(v.strip()) or _looks_decimal(v))
    if numericish >= max(1, int(len(samples) * 0.6)) and (
        "amount" in lower_name or "measurement" in lower_name or "price" in lower_name
    ):
        if any(_fraction_len(v) > 0 for v in samples if _looks_decimal(v) or _INT_RE.match(v.strip())):
            return ColumnSchema(name=name, type=ColumnType.DOUBLE)
        return ColumnSchema(name=name, type=ColumnType.INTEGER)

    return ColumnSchema(name=name, type=ColumnType.STRING)


def _looks_decimal(value: str) -> bool:
    v = value.strip().replace(",", "")
    if v.startswith("$"):
        return False
    return bool(_DECIMAL_RE.match(v) or _INT_RE.match(v))


def _fraction_len(value: str) -> int:
    v = value.strip().replace(",", "")
    if "." not in v:
        return 0
    return len(v.split(".", 1)[1])


def parse_date(value: str) -> datetime | None:
    v = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    # Catch invalid calendar dates like 2026-02-30 via fromisoformat after normalize
    if _ISO_DATE.match(v):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    return None
