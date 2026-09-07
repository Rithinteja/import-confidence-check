from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ColumnType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BIGINT = "bigint"
    DOUBLE = "double"
    DECIMAL = "decimal"
    DATE = "date"
    TIMESTAMP = "timestamp"
    BOOLEAN = "boolean"


class DecimalParams(BaseModel):
    precision: int = 10
    scale: int = 0


class ColumnSchema(BaseModel):
    name: str
    type: ColumnType
    decimal: Optional[DecimalParams] = None


class RiskCategory(str, Enum):
    LEADING_ZERO_LOSS = "leading_zero_loss"
    IDENTIFIER_COLLISION = "identifier_collision"
    DECIMAL_PRECISION_LOSS = "decimal_precision_loss"
    DECIMAL_SCALE_ROUNDING = "decimal_scale_rounding"
    INVALID_DATE = "invalid_date"
    INVALID_TIMESTAMP = "invalid_timestamp"
    NULL_AFTER_CONVERSION = "null_after_conversion"
    LARGE_INTEGER_PRECISION = "large_integer_precision"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskExample(BaseModel):
    row: int
    original: str
    converted: Optional[str] = None
    reason: str = ""
    outside_preview: bool = False


class ImportRisk(BaseModel):
    risk_id: str
    column: str
    category: RiskCategory
    severity: Severity
    affected_rows: int
    scanned_rows: int
    examples: list[RiskExample] = Field(default_factory=list)
    explanation: str
    recommended_type: ColumnType
    recommended_action: str
    recommended_decimal: Optional[DecimalParams] = None
    outside_preview_count: int = 0
    title: str = ""


class ParsedTable(BaseModel):
    headers: list[str]
    rows: list[list[str]]
    filename: str
    size_bytes: int
    format: Literal["csv", "tsv", "json", "xlsx"]


class ImportSessionResponse(BaseModel):
    session_id: str
    filename: str
    size_bytes: int
    format: str
    catalog: str = "dbacademy"
    schema_name: str = Field(default="default", alias="schema", serialization_alias="schema")
    table_name: str
    action: str = "Create new table"
    columns: list[ColumnSchema]
    preview_rows: list[dict[str, str]]
    preview_limit: int
    total_rows: int
    risks: list[ImportRisk]
    confidence_status: str
    unresolved_count: int
    resolved_count: int = 0
    risks_outside_preview: bool = False

    model_config = {"populate_by_name": True, "ser_json_by_alias": True}


class RescanRequest(BaseModel):
    columns: list[ColumnSchema]


class ApplyFixRequest(BaseModel):
    risk_id: str


class CreateTableRequest(BaseModel):
    force: bool = False


class CreatedTableResponse(BaseModel):
    catalog: str
    schema_name: str = Field(alias="schema", serialization_alias="schema")
    table_name: str
    columns: list[ColumnSchema]
    sample_rows: list[dict[str, Any]]
    total_rows: int
    owner: str = "rithi@example.com"
    created_at: str
    table_type: str = "Managed Delta"
    size_label: str
    import_summary: list[str]
    unresolved_risks: list[ImportRisk] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "ser_json_by_alias": True}


class SampleFileInfo(BaseModel):
    id: str
    label: str
    filename: str
    description: str


class GroqExplainRequest(BaseModel):
    risk: ImportRisk
    column_role: str = ""


class GroqAskRequest(BaseModel):
    question: str
    risk_categories: list[str] = Field(default_factory=list)
    column_roles: list[str] = Field(default_factory=list)
    affected_row_counts: dict[str, int] = Field(default_factory=dict)
    masked_examples: list[dict[str, str]] = Field(default_factory=list)
    proposed_schema: dict[str, str] = Field(default_factory=dict)
    resolved_risks: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)


class GroqSummaryRequest(BaseModel):
    unresolved_risks: list[ImportRisk]
    resolved_risks: list[ImportRisk] = Field(default_factory=list)
    total_rows: int
    preview_limit: int = 50


class GroqTextResponse(BaseModel):
    text: str
    source: Literal["groq", "fallback"]
    ai_available: bool
