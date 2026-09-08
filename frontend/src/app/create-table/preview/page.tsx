"use client";

import { api, ColumnType, ImportRisk, ImportSession } from "@/lib/api";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

const TYPES: ColumnType[] = [
  "string",
  "integer",
  "bigint",
  "double",
  "decimal",
  "date",
  "timestamp",
  "boolean",
];

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function valueText(value: unknown) {
  if (value === null || value === undefined) return "null";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function PreviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const sessionId = params.get("session") || "";
  const [data, setData] = useState<ImportSession | null>(null);
  const [error, setError] = useState("");
  const [working, setWorking] = useState("");
  const [drawer, setDrawer] = useState<ImportRisk | null>(null);
  const [modal, setModal] = useState(false);
  const [askOpen, setAskOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [aiSummary, setAiSummary] = useState("");
  const [aiSummarySource, setAiSummarySource] = useState<"groq" | "fallback" | "">("");
  const [aiByRisk, setAiByRisk] = useState<Record<string, { text: string; source: string }>>({});
  const [advancedOpen, setAdvancedOpen] = useState(true);

  useEffect(() => {
    if (!sessionId) {
      setError("No import session was provided.");
      return;
    }
    api
      .session(sessionId)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [sessionId]);

  const schemaName = data?.schema_name || data?.schema || "default";
  const activeRisks = useMemo(() => data?.risks || [], [data]);
  const riskKey = useMemo(
    () => activeRisks.map((r) => r.risk_id).join("|"),
    [activeRisks],
  );

  useEffect(() => {
    if (!data) return;
    let cancelled = false;

    async function loadAi() {
      try {
        const summary = await api.importSummary({
          unresolved_risks: data!.risks,
          resolved_risks: [],
          total_rows: data!.total_rows,
          preview_limit: data!.preview_limit,
        });
        if (!cancelled) {
          setAiSummary(summary.text);
          setAiSummarySource(summary.source as "groq" | "fallback");
        }
      } catch {
        if (!cancelled) {
          setAiSummary("");
          setAiSummarySource("fallback");
        }
      }

      const entries = await Promise.all(
        data!.risks.map(async (risk) => {
          try {
            const result = await api.explainRisk({
              risk,
              column_role: risk.column.replaceAll("_", " "),
            });
            return [risk.risk_id, { text: result.text, source: result.source }] as const;
          } catch {
            return [risk.risk_id, { text: risk.explanation, source: "fallback" }] as const;
          }
        }),
      );
      if (!cancelled) {
        setAiByRisk(Object.fromEntries(entries));
      }
    }

    void loadAi();
    return () => {
      cancelled = true;
    };
  }, [data?.session_id, riskKey]);

  async function rescan(index: number, type: ColumnType) {
    if (!data) return;
    const columns = data.columns.map((column, i) =>
      i === index ? { ...column, type } : column,
    );
    setData({ ...data, columns });
    setWorking(`column-${index}`);
    try {
      setData(await api.rescan(sessionId, columns));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rescan failed");
    } finally {
      setWorking("");
    }
  }

  async function applyFix(risk: ImportRisk) {
    setWorking(risk.risk_id);
    try {
      setData(await api.applyFix(sessionId, risk.risk_id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not apply fix");
    } finally {
      setWorking("");
    }
  }

  async function saveMeta(
    field: "catalog" | "schema" | "table_name" | "action" | "infer_timestamps",
    value: string | boolean,
  ) {
    if (!data) return;
    if (typeof value === "string" && !value.trim()) return;
    try {
      setData(
        await api.updateMeta(
          sessionId,
          typeof value === "boolean"
            ? { infer_timestamps: value }
            : { [field]: value.trim() },
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save table settings");
    }
  }

  async function create(force: boolean) {
    if (!data) return;
    setWorking("create");
    try {
      await api.create(sessionId, force);
      router.push(
        `/catalog/table?catalog=${encodeURIComponent(data.catalog)}&schema=${encodeURIComponent(schemaName)}&table=${encodeURIComponent(data.table_name)}&session=${encodeURIComponent(sessionId)}`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Table creation failed");
      setModal(false);
      setWorking("");
    }
  }

  async function ask() {
    if (!question.trim() || !data) return;
    setWorking("ask");
    setAnswer("");
    try {
      const result = await api.ask({
        question,
        risk_categories: activeRisks.map((risk) => risk.category),
        affected_row_counts: Object.fromEntries(
          activeRisks.map((risk) => [risk.column, risk.affected_rows]),
        ),
        proposed_schema: Object.fromEntries(
          data.columns.map((column) => [column.name, column.type]),
        ),
        unresolved_risks: activeRisks.map((risk) => risk.title),
      });
      setAnswer(String(result.text ?? "No response returned."));
    } catch (e) {
      setAnswer(e instanceof Error ? e.message : "Unable to answer");
    } finally {
      setWorking("");
    }
  }

  if (error && !data) {
    return (
      <div className="page-content">
        <div className="error-state">
          <h2>Unable to open preview</h2>
          <p>{error}</p>
          <Link className="primary-button" href="/create-table">
            Back to upload
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="page-content loading-state">
        <span className="spinner" />
        Analyzing your import…
      </div>
    );
  }

  return (
    <div className="preview-page">
      <div className="preview-header">
        <nav className="breadcrumb" aria-label="Breadcrumb">
          <Link href="/">Add data</Link>
          <span>/</span>
          <Link href="/create-table">Create table from file</Link>
          <span>/</span>
          <span>Preview</span>
        </nav>
        <div className="file-heading">
          <span className="file-icon">{(data.format || "csv").toUpperCase()}</span>
          <div>
            <h1>{data.filename}</h1>
            <p>
              {formatBytes(data.size_bytes)} · {data.format?.toUpperCase()} ·{" "}
              {data.total_rows.toLocaleString()} rows
            </p>
          </div>
        </div>
      </div>

      {error ? (
        <div className="error-banner inline" role="alert">
          {error}
          <button type="button" onClick={() => setError("")}>
            Close
          </button>
        </div>
      ) : null}

      <div className="preview-workspace">
        <div className="preview-main">
          <section className="destination-card" aria-labelledby="destination-heading">
            <h2 id="destination-heading">Table destination</h2>
            <div className="meta-grid">
              <label>
                Catalog
                <input
                  defaultValue={data.catalog}
                  onBlur={(e) => void saveMeta("catalog", e.target.value)}
                />
              </label>
              <label>
                Schema
                <input
                  defaultValue={schemaName}
                  onBlur={(e) => void saveMeta("schema", e.target.value)}
                />
              </label>
              <label>
                Table name
                <input
                  defaultValue={data.table_name}
                  onBlur={(e) => void saveMeta("table_name", e.target.value)}
                />
              </label>
              <label>
                Action
                <select
                  defaultValue={data.action}
                  onChange={(e) => void saveMeta("action", e.target.value)}
                >
                  <option value="Create new table">Create new table</option>
                  <option value="Append">Append</option>
                  <option value="Overwrite">Overwrite</option>
                </select>
              </label>
            </div>
            {data.show_infer_timestamps ? (
              <div className="advanced-attrs">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => setAdvancedOpen((open) => !open)}
                >
                  {advancedOpen ? "Hide advanced attributes" : "Advanced attributes"}
                </button>
                {advancedOpen ? (
                  <label className="advanced-check">
                    <input
                      type="checkbox"
                      checked={Boolean(data.infer_timestamps)}
                      onChange={(e) => void saveMeta("infer_timestamps", e.target.checked)}
                    />
                    <span>
                      Infer timestamp
                      <small>
                        When on, JSON digit strings like 000123 become timestamps
                        (0123-01-01T00:00:00.000Z).
                      </small>
                    </span>
                  </label>
                ) : null}
              </div>
            ) : null}
          </section>

          <section className="data-preview" aria-labelledby="preview-heading">
            <div className="section-title-row">
              <div>
                <h2 id="preview-heading">Data preview</h2>
                <p>
                  Showing {Math.min(data.preview_rows.length, 50)} of{" "}
                  {data.total_rows.toLocaleString()} rows
                </p>
              </div>
            </div>
            <div className="table-scroll">
              <table className="data-grid">
                <thead>
                  <tr>
                    <th className="row-number">#</th>
                    {data.columns.map((column, i) => (
                      <th key={`${column.name}-${i}`}>
                        <strong>{column.name}</strong>
                        <select
                          aria-label={`Type for ${column.name}`}
                          value={column.type}
                          disabled={working === `column-${i}`}
                          onChange={(e) =>
                            void rescan(i, e.target.value as ColumnType)
                          }
                        >
                          {TYPES.map((type) => (
                            <option key={type}>{type}</option>
                          ))}
                        </select>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.preview_rows.slice(0, 50).map((row, i) => (
                    <tr key={i}>
                      <td className="row-number">{i + 1}</td>
                      {data.columns.map((column) => {
                        const risky = activeRisks.some(
                          (r) =>
                            r.column === column.name &&
                            r.examples.some((x) => x.row === i || x.row === i + 1),
                        );
                        return (
                          <td
                            className={risky ? "risky-cell" : ""}
                            title={valueText(row[column.name])}
                            key={column.name}
                          >
                            {valueText(row[column.name])}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="confidence-panel" aria-labelledby="confidence-heading">
          <div className="confidence-title">
            <h2 id="confidence-heading">Import Confidence Check</h2>
            <span
              className={`status-pill ${data.unresolved_count ? "warning" : "good"}`}
            >
              {data.confidence_status}
            </span>
          </div>

          {aiSummary ? (
            <div className="ai-summary">
              <div className="ai-label">
                {aiSummarySource === "fallback"
                  ? "Built-in summary"
                  : "AI / LLM generated report"}
              </div>
              <p className="ai-summary-text">{aiSummary}</p>
            </div>
          ) : (
            <p className="confidence-copy">
              Scanned all {data.total_rows.toLocaleString()} rows for conversions that
              could change meaning.
            </p>
          )}

          <div className="scan-summary" aria-label="Scan summary">
            <span>
              <strong>{data.unresolved_count}</strong>
              unresolved
            </span>
            <span>
              <strong>{data.resolved_count}</strong>
              fixed
            </span>
            <span>
              <strong>{data.risks_outside_preview ? "Yes" : "No"}</strong>
              beyond preview
            </span>
          </div>

          <div className="risk-list">
            {activeRisks.length === 0 ? (
              <div className="all-clear">
                <strong>Important values preserved</strong>
                <p>
                  No conversion risks found across {data.total_rows.toLocaleString()} checked
                  rows. Ready to create the table.
                </p>
              </div>
            ) : null}

            {activeRisks.map((risk) => {
              const ai = aiByRisk[risk.risk_id];
              return (
                <article className="risk-card" key={risk.risk_id}>
                  <div className="risk-card-head">
                    <span
                      className={`severity-dot ${risk.severity}`}
                      aria-label={`${risk.severity} severity`}
                    />
                    <div>
                      <h3>{risk.title}</h3>
                      <p>
                        Column <code>{risk.column}</code>
                      </p>
                    </div>
                  </div>

                  {risk.examples[0] ? (
                    <div className="compare-pair">
                      <div>
                        <span>Original</span>
                        <code>{valueText(risk.examples[0].original)}</code>
                      </div>
                      <div>
                        <span>Proposed</span>
                        <code>
                          {valueText(
                            risk.examples[0].converted ?? risk.examples[0].proposed,
                          )}
                        </code>
                      </div>
                    </div>
                  ) : null}

                  <p className="risk-explanation">
                    {ai?.text || risk.explanation}
                  </p>
                  <div className="ai-label">
                    {ai?.source === "groq"
                      ? "AI / LLM generated report"
                      : ai?.source === "fallback"
                        ? "Built-in explanation"
                        : "Loading explanation…"}
                  </div>

                  <div className="risk-stats">
                    <strong>{risk.affected_rows.toLocaleString()}</strong> of{" "}
                    {risk.scanned_rows.toLocaleString()} rows affected
                    {risk.outside_preview_count > 0 ? (
                      <span className="outside-note">
                        Found outside the visible preview
                      </span>
                    ) : null}
                  </div>

                  <div className="risk-actions">
                    <button
                      className="primary-small"
                      type="button"
                      disabled={working === risk.risk_id}
                      onClick={() => void applyFix(risk)}
                    >
                      {working === risk.risk_id
                        ? "Applying…"
                        : risk.recommended_action || "Apply recommended fix"}
                    </button>
                    <button
                      className="link-button"
                      type="button"
                      onClick={() => setDrawer(risk)}
                    >
                      View affected rows
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          <button
            className="ask-button"
            type="button"
            onClick={() => setAskOpen(!askOpen)}
          >
            Ask about this import
          </button>
          {askOpen ? (
            <div className="ask-box">
              <label className="sr-only" htmlFor="ask-input">
                Question about this import
              </label>
              <textarea
                id="ask-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Why should this column remain a String?"
              />
              <button
                className="secondary-button"
                type="button"
                disabled={working === "ask"}
                onClick={() => void ask()}
              >
                {working === "ask" ? "Asking…" : "Ask"}
              </button>
              {answer ? <p className="ask-answer">{answer}</p> : null}
            </div>
          ) : null}

          <div className="create-area">
            <button
              className="primary-button wide"
              type="button"
              onClick={() => setModal(true)}
            >
              Create table
            </button>
            <p>
              {data.unresolved_count
                ? `${data.unresolved_count} risk${data.unresolved_count === 1 ? "" : "s"} remaining`
                : "All checks passed"}
            </p>
          </div>
        </aside>
      </div>

      {drawer ? (
        <div className="overlay" onMouseDown={() => setDrawer(null)}>
          <aside
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="drawer-head">
              <div>
                <h2 id="drawer-title">Affected rows</h2>
                <p>
                  {drawer.title} · <code>{drawer.column}</code>
                </p>
              </div>
              <button type="button" onClick={() => setDrawer(null)}>
                Close
              </button>
            </div>
            <div className="drawer-summary">
              {drawer.affected_rows.toLocaleString()} rows may change during import.
            </div>
            <table className="affected-table">
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Original</th>
                  <th>Proposed</th>
                </tr>
              </thead>
              <tbody>
                {drawer.examples.map((example, i) => (
                  <tr key={i}>
                    <td>
                      {example.row}
                      {example.outside_preview ? (
                        <span className="outside-badge">Outside preview</span>
                      ) : null}
                    </td>
                    <td>{valueText(example.original)}</td>
                    <td>{valueText(example.converted ?? example.proposed)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </aside>
        </div>
      ) : null}

      {modal ? (
        <div className="overlay modal-overlay">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <div
              className={`modal-symbol ${data.unresolved_count ? "warning" : "good"}`}
            >
              {data.unresolved_count ? "!" : "OK"}
            </div>
            <h2 id="modal-title">
              {data.unresolved_count
                ? "Create table with unresolved risks?"
                : "Ready to create table"}
            </h2>
            <p>
              {data.unresolved_count
                ? `${data.unresolved_count} conversion risk${data.unresolved_count === 1 ? "" : "s"} could change values. Fix them, or create anyway.`
                : `Create ${data.catalog}.${schemaName}.${data.table_name} with ${data.total_rows.toLocaleString()} rows?`}
            </p>
            <div className="modal-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(false)}
              >
                Go back
              </button>
              <button
                className={data.unresolved_count ? "danger-button" : "primary-button"}
                type="button"
                disabled={working === "create"}
                onClick={() => void create(data.unresolved_count > 0)}
              >
                {working === "create"
                  ? "Creating…"
                  : data.unresolved_count
                    ? "Create anyway"
                    : "Create table"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function PreviewPage() {
  return (
    <Suspense
      fallback={
        <div className="page-content loading-state">Loading preview…</div>
      }
    >
      <PreviewContent />
    </Suspense>
  );
}
