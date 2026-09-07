from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from app.models import ColumnSchema, ColumnType, DecimalParams
from app.services.infer import parse_date

_INT_RE = re.compile(r"^[+-]?\d+$")
_TS_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?$"
)


def convert_value(raw: str, column: ColumnSchema) -> Optional[str]:
    """Simulate stored value under proposed type. Empty stays empty (not null warning)."""
    if raw is None:
        return None
    text = str(raw)
    if text.strip() == "":
        return ""

    t = column.type
    if t == ColumnType.STRING:
        return text
    if t == ColumnType.BOOLEAN:
        return _as_bool(text)
    if t == ColumnType.INTEGER:
        return _as_int(text, bits=32)
    if t == ColumnType.BIGINT:
        return _as_int(text, bits=64)
    if t == ColumnType.DOUBLE:
        return _as_double(text)
    if t == ColumnType.DECIMAL:
        params = column.decimal or DecimalParams()
        return _as_decimal(text, params)
    if t == ColumnType.DATE:
        return _as_date(text)
    if t == ColumnType.TIMESTAMP:
        return _as_timestamp(text)
    return text


def _as_bool(text: str) -> Optional[str]:
    v = text.strip().lower()
    if v in {"true", "yes", "1"}:
        return "true"
    if v in {"false", "no", "0"}:
        return "false"
    return None


def _as_int(text: str, bits: int) -> Optional[str]:
    v = text.strip().replace(",", "")
    if v.startswith("$"):
        return None
    # European decimal not an int
    if re.search(r"\d,\d", v) and "." not in v:
        return None
    if not _INT_RE.match(v) and not re.match(r"^[+-]?\d+\.0+$", v):
        if re.match(r"^[+-]?\d+\.\d+$", v):
            # truncation path like float→int? treat as null for strict int
            return None
        return None
    try:
        n = int(v.split(".")[0])
    except ValueError:
        return None
    if bits == 32 and not (-(2**31) <= n <= 2**31 - 1):
        return None
    return str(n)


def _as_double(text: str) -> Optional[str]:
    v = text.strip().replace(",", "")
    if v.startswith("$"):
        v = v[1:].replace(",", "")
    # European format 1.234,56
    if re.match(r"^\d{1,3}(\.\d{3})*,\d+$", text.strip()):
        return None
    if v.lower() in {"unknown", "null", "nan"}:
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    # JavaScript / IEEE double stringification (prototype approximation)
    return repr(float(f)) if abs(f) >= 1e16 else format(f, ".15g")


def _as_decimal(text: str, params: DecimalParams) -> Optional[str]:
    v = text.strip().replace(",", "")
    if v.startswith("$"):
        return None
    if v.lower() in {"unknown", "null"}:
        return None
    try:
        d = Decimal(v)
    except InvalidOperation:
        return None
    quant = Decimal(1).scaleb(-params.scale)
    try:
        rounded = d.quantize(quant, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None
    return format(rounded, "f")


def _as_date(text: str) -> Optional[str]:
    dt = parse_date(text)
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")


def _as_timestamp(text: str) -> Optional[str]:
    v = text.strip()
    if _INT_RE.match(v) and len(v) >= 5:
        # Identifier-like numbers should not become timestamps; return a fake conversion
        # only if inference chose timestamp; mark as converted epoch-ish string
        return None
    if _TS_RE.match(v):
        return v.replace("T", " ")
    dt = parse_date(v)
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d 00:00:00")


def materialize_row(raw_row: list[str], columns: list[ColumnSchema]) -> dict[str, Optional[str]]:
    out: dict[str, Optional[str]] = {}
    for i, col in enumerate(columns):
        raw = raw_row[i] if i < len(raw_row) else ""
        out[col.name] = convert_value(raw, col)
    return out
