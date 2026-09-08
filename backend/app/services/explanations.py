from __future__ import annotations

from app.models import ImportRisk, RiskCategory


def fallback_explain(risk: ImportRisk, column_role: str = "") -> str:
    role = column_role or risk.column.replace("_", " ")
    example = ""
    if risk.examples:
        original = risk.examples[0].original
        converted = risk.examples[0].converted
        if original is not None and converted is not None:
            example = f" Example: {original} → {converted}."

    mapping = {
        RiskCategory.LEADING_ZERO_LOSS: (
            f"{risk.affected_rows} values in {role} lose leading zeros.{example} "
            "Keep as String so IDs and codes stay exact."
        ),
        RiskCategory.IDENTIFIER_COLLISION: (
            f"Different {role} values would store as the same value after conversion. "
            "Keep as String so records do not merge."
        ),
        RiskCategory.DECIMAL_PRECISION_LOSS: (
            f"{role} may lose digits as Double.{example} Prefer Decimal with enough scale."
        ),
        RiskCategory.DECIMAL_SCALE_ROUNDING: (
            f"{role} values can round under the proposed scale "
            "(for example 19.99 → 20). Use a scale that keeps the cents."
        ),
        RiskCategory.INVALID_DATE: (
            f"{risk.affected_rows} non-empty {role} values become null as Date. "
            "Keep as String or clean the source values."
        ),
        RiskCategory.INVALID_TIMESTAMP: (
            f"{role} looks like an ID being read as a timestamp.{example} "
            "Keep as String, or turn off timestamp inference."
        ),
        RiskCategory.NULL_AFTER_CONVERSION: (
            f"{risk.affected_rows} non-empty {role} values become null under the proposed type. "
            "Review the values or keep as String."
        ),
        RiskCategory.LARGE_INTEGER_PRECISION: (
            f"{role} includes integers too large for exact floating-point storage. "
            "Prefer String or Decimal."
        ),
    }
    return mapping.get(risk.category, risk.explanation)


def _risk_line(risk: ImportRisk) -> str:
    title = risk.title or risk.column
    bits = [f"- {title} ({risk.severity.value}): {risk.affected_rows} row(s)"]
    if risk.examples:
        original = risk.examples[0].original
        converted = risk.examples[0].converted
        if original is not None and converted is not None:
            bits.append(f"  e.g. {original} → {converted}")
    if risk.outside_preview_count > 0:
        bits.append("  some rows are past the visible preview")
    return "\n".join(bits)


def fallback_summary(
    unresolved: list[ImportRisk],
    resolved: list[ImportRisk],
    total_rows: int,
    preview_limit: int,
) -> str:
    if not unresolved and not resolved:
        return f"Scanned {total_rows} rows.\nNo conversion risks found.\nReady to create the table."
    if not unresolved and resolved:
        return (
            f"Scanned {total_rows} rows.\n"
            f"{len(resolved)} risk(s) fixed.\n"
            "Important values are preserved under the current schema."
        )

    lines = [
        f"Scanned {total_rows} rows. Found {len(unresolved)} open risk(s):",
        "",
    ]
    for risk in unresolved[:5]:
        lines.append(_risk_line(risk))
    if len(unresolved) > 5:
        lines.append(f"- …and {len(unresolved) - 5} more")
    outside = sum(1 for r in unresolved if r.outside_preview_count > 0)
    if outside:
        lines.append("")
        lines.append(
            f"{outside} of these show up past the first {preview_limit} preview rows."
        )
    if resolved:
        lines.append("")
        lines.append(f"{len(resolved)} risk(s) already fixed.")
    return "\n".join(lines)


def fallback_ask(question: str, unresolved: list[str], resolved: list[str]) -> str:
    q = question.lower()
    if "leading zero" in q or "leading zeros" in q:
        return (
            "Leading zeros often encode meaning in identifiers and postal codes. "
            "If they are stored as numbers, 000123 becomes 123 and may no longer join to upstream systems. "
            "Keeping the column as String preserves the original value."
        )
    if "first" in q or "priorit" in q:
        if unresolved:
            return (
                f"Fix high-severity identifier and rounding risks first. "
                f"Unresolved items currently include: {', '.join(unresolved[:5])}."
            )
        return "No unresolved risks remain. You can create the table."
    if "preview" in q or "row 50" in q or "outside" in q:
        return (
            "The grid shows the first 50 rows for readability, but Import Confidence Check scans the full file. "
            "Risks after row 50 are labeled “Found outside the visible preview.”"
        )
    if "create anyway" in q or "anyway" in q:
        return (
            "Creating anyway keeps the proposed types and may store altered values. "
            "High-severity risks can break joins, reporting, and financial totals. "
            "Prefer applying the recommended String/Decimal fixes first."
        )
    if "string" in q:
        return (
            "String is recommended when the source text must be preserved exactly, "
            "especially IDs, postal codes, and values that only look numeric."
        )
    return (
        "I can explain conversion risks from the scan report. "
        f"Unresolved: {', '.join(unresolved) or 'none'}. "
        f"Resolved: {', '.join(resolved) or 'none'}."
    )
