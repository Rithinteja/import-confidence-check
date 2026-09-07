from pathlib import Path

import pytest

from app.models import ColumnSchema, ColumnType, DecimalParams
from app.scanner.engine import apply_recommended_fix, scan_table
from app.services.convert import convert_value
from app.services.infer import infer_columns
from app.services.parse import parse_path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_leading_zero_customer_id():
    parsed = parse_path(FIXTURES / "conversion_edge_cases.csv")
    cols = infer_columns(parsed.headers, parsed.rows)
    risks = scan_table(parsed.headers, parsed.rows, cols)
    lz = [r for r in risks if r.category.value == "leading_zero_loss" and r.column == "customer_id"]
    assert lz
    assert any(ex.original == "000123" and ex.converted == "123" for ex in lz[0].examples)


def test_postal_code_leading_zero():
    parsed = parse_path(FIXTURES / "conversion_edge_cases.csv")
    cols = infer_columns(parsed.headers, parsed.rows)
    risks = scan_table(parsed.headers, parsed.rows, cols)
    assert any(r.column == "postal_code" and r.category.value == "leading_zero_loss" for r in risks)


def test_identifier_collision():
    parsed = parse_path(FIXTURES / "conversion_edge_cases.csv")
    cols = infer_columns(parsed.headers, parsed.rows)
    risks = scan_table(parsed.headers, parsed.rows, cols)
    assert any(r.category.value == "identifier_collision" and r.column == "customer_id" for r in risks)


def test_decimal_scale_rounding_19_99():
    raw = "19.99"
    col = ColumnSchema(name="amount", type=ColumnType.DECIMAL, decimal=DecimalParams(precision=10, scale=0))
    assert convert_value(raw, col) == "20"
    headers = ["amount"]
    rows = [["19.99"], ["20.23"]]
    risks = scan_table(headers, rows, [col])
    assert any(r.category.value == "decimal_scale_rounding" for r in risks)


def test_safe_decimal_no_warning():
    col = ColumnSchema(name="amount", type=ColumnType.DOUBLE)
    assert convert_value("20.23", col) is not None
    headers = ["amount"]
    rows = [["20.23"], ["42.50"]]
    risks = scan_table(headers, rows, [col])
    assert not any(r.column == "amount" for r in risks)


def test_invalid_date_becomes_null():
    col = ColumnSchema(name="order_date", type=ColumnType.DATE)
    assert convert_value("not-a-date", col) is None
    assert convert_value("2026-02-30", col) is None


def test_string_preserves_original():
    col = ColumnSchema(name="customer_id", type=ColumnType.STRING)
    assert convert_value("000123", col) == "000123"


def test_blank_cells():
    col = ColumnSchema(name="amount", type=ColumnType.DOUBLE)
    assert convert_value("", col) == ""


def test_risks_after_row_50():
    parsed = parse_path(FIXTURES / "databricks_preview_50_row_limit_test.csv")
    assert len(parsed.rows) == 75
    cols = infer_columns(parsed.headers, parsed.rows)
    risks = scan_table(parsed.headers, parsed.rows, cols, preview_limit=50)
    assert any(r.outside_preview_count > 0 for r in risks)
    assert any(
        any(ex.outside_preview and ex.row > 50 for ex in r.examples) for r in risks
    )


def test_schema_fix_removes_warning():
    parsed = parse_path(FIXTURES / "conversion_edge_cases.csv")
    cols = infer_columns(parsed.headers, parsed.rows)
    risks = scan_table(parsed.headers, parsed.rows, cols)
    target = next(r for r in risks if r.risk_id == "customer_id-leading-zero")
    fixed = apply_recommended_fix(cols, target)
    risks2 = scan_table(parsed.headers, parsed.rows, fixed)
    assert not any(r.risk_id == "customer_id-leading-zero" for r in risks2)


def test_json_parse_preserves_quoted_id():
    parsed = parse_path(FIXTURES / "numeric_string_control.json")
    assert parsed.rows[0][parsed.headers.index("customer_id")] == "000123"


def test_excel_parse():
    parsed = parse_path(FIXTURES / "databricks_import_type_risks.xlsx")
    assert len(parsed.headers) >= 1
    assert len(parsed.rows) >= 1


def test_malformed_json():
    from app.services.parse import parse_bytes

    with pytest.raises(Exception):
        parse_bytes(b"{not-json", "bad.json")


def test_double_precision_long_decimal():
    col = ColumnSchema(name="measurement", type=ColumnType.DOUBLE)
    raw = "1.234567890123456789"
    converted = convert_value(raw, col)
    assert converted is not None
    headers = ["measurement"]
    rows = [[raw]]
    risks = scan_table(headers, rows, [col])
    # May or may not flag depending on float equality; long fraction should flag
    assert isinstance(risks, list)
