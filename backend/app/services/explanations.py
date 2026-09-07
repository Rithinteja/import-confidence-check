from __future__ import annotations

from app.models import ImportRisk, RiskCategory


def fallback_explain(risk: ImportRisk, column_role: str = "") -> str:
    role = column_role or risk.column.replace("_", " ")
    mapping = {
        RiskCategory.LEADING_ZERO_LOSS: (
            f"{risk.affected_rows} values in {role} will lose leading zeros "
            f"(example {risk.examples[0].original if risk.examples else ''} → "
            f"{risk.examples[0].converted if risk.examples else ''}). "
            "This can break joins and lookups. Keep the column as String."
        ),
        RiskCategory.IDENTIFIER_COLLISION: (
            f"Distinct {role} values will store as the same value after conversion, "
            "which can merge different records. Keep the column as String."
        ),
        RiskCategory.DECIMAL_PRECISION_LOSS: (
            f"{role} may lose digits when stored as Double, which can change measurements or totals. "
            "Prefer Decimal with enough scale."
        ),
        RiskCategory.DECIMAL_SCALE_ROUNDING: (
            f"{role} values such as 19.99 may round (for example to 20) under the proposed decimal scale. "
            "Use a scale that preserves cents."
        ),
        RiskCategory.INVALID_DATE: (
            f"{risk.affected_rows} non-empty {role} values become null as Date, which can drop records "
            "from time-based analysis. Keep as String or clean the source values."
        ),
        RiskCategory.INVALID_TIMESTAMP: (
            f"{role} appears to include identifier-like values being read as timestamps. "
            "Keep as String to preserve the original values."
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


def fallback_summary(
    unresolved: list[ImportRisk],
    resolved: list[ImportRisk],
    total_rows: int,
    preview_limit: int,
) -> str:
    if not unresolved and not resolved:
        return f"Scanned {total_rows} rows. No conversion risks found. Ready to create the table."
    if not unresolved and resolved:
        return (
            f"Scanned {total_rows} rows. {len(resolved)} risk(s) fixed. "
            "Important values are preserved under the current schema."
        )
    outside = sum(1 for r in unresolved if r.outside_preview_count > 0)
    parts = [
        f"{len(unresolved)} conversion risk(s) found across {total_rows} rows."
    ]
    top = unresolved[0]
    parts.append(f"Highest priority: {top.title or top.column} ({top.severity.value}).")
    if outside:
        parts.append(
            f"{outside} risk(s) include issues found outside the visible {preview_limit}-row preview."
        )
    if resolved:
        parts.append(f"{len(resolved)} risk(s) already fixed.")
    return " ".join(parts)


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
