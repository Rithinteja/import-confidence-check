export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export type ColumnType =
  | "string"
  | "integer"
  | "bigint"
  | "double"
  | "decimal"
  | "date"
  | "timestamp"
  | "boolean";

export interface ColumnSchema {
  name: string;
  type: ColumnType;
  decimal?: { precision: number; scale: number };
}

export interface RiskExample {
  row: number;
  original: unknown;
  converted?: unknown;
  proposed?: unknown;
  reason: string;
  outside_preview?: boolean;
}

export interface ImportRisk {
  risk_id: string;
  column: string;
  category: string;
  severity: string;
  affected_rows: number;
  scanned_rows: number;
  examples: RiskExample[];
  explanation: string;
  recommended_type?: ColumnType;
  recommended_action: string;
  recommended_decimal?: { precision: number; scale: number };
  outside_preview_count: number;
  title: string;
}

export interface ImportSession {
  session_id: string;
  filename: string;
  size_bytes: number;
  format: string;
  catalog: string;
  schema?: string;
  schema_name?: string;
  table_name: string;
  action: string;
  columns: ColumnSchema[];
  preview_rows: Record<string, unknown>[];
  preview_limit: number;
  total_rows: number;
  risks: ImportRisk[];
  confidence_status: string;
  unresolved_count: number;
  resolved_count: number;
  risks_outside_preview: number | boolean;
  infer_timestamps?: boolean;
  show_infer_timestamps?: boolean;
  [key: string]: unknown;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  samples: () => request<Array<Record<string, unknown>>>("/api/samples"),
  sampleFileUrl: (id: string) =>
    `${API_BASE}/api/samples/${encodeURIComponent(id)}/file`,
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<ImportSession>("/api/import/upload", { method: "POST", body });
  },
  loadSample: (id: string) =>
    request<ImportSession>(`/api/import/sample/${encodeURIComponent(id)}`, {
      method: "POST",
    }),
  session: (id: string) => request<ImportSession>(`/api/import/${id}`),
  rescan: (id: string, columns: ColumnSchema[]) =>
    request<ImportSession>(`/api/import/${id}/rescan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ columns }),
    }),
  applyFix: (id: string, riskId: string) =>
    request<ImportSession>(`/api/import/${id}/apply-fix`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ risk_id: riskId }),
    }),
  updateMeta: (
    id: string,
    body: Partial<
      Pick<ImportSession, "table_name" | "catalog" | "action" | "infer_timestamps">
    > & {
      schema?: string;
    },
  ) =>
    request<ImportSession>(`/api/import/${id}/meta`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  create: (id: string, force: boolean) =>
    request<Record<string, unknown>>(`/api/import/${id}/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ force }),
    }),
  created: (id: string) =>
    request<Record<string, unknown>>(`/api/import/${id}/created`),
  tables: () =>
    request<
      Array<{
        session_id: string;
        catalog: string;
        schema: string;
        table_name: string;
        created_at: string;
        total_rows: number;
        size_label: string;
        owner: string;
      }>
    >("/api/tables"),
  ask: (body: Record<string, unknown>) =>
    request<{ text: string; source: string; ai_available: boolean }>("/api/groq/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  explainRisk: (body: Record<string, unknown>) =>
    request<{ text: string; source: string; ai_available: boolean }>("/api/groq/explain-risk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  importSummary: (body: Record<string, unknown>) =>
    request<{ text: string; source: string; ai_available: boolean }>("/api/groq/import-summary", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
