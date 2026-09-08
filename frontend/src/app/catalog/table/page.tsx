"use client";

import { api } from "@/lib/api";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

function text(value: unknown) {
  if (value === null || value === undefined) return "null";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function CatalogContent() {
  const search = useSearchParams();
  const sessionId = search.get("session") || "";
  const catalog = search.get("catalog") || "dbacademy";
  const schema = search.get("schema") || "default";
  const table = search.get("table") || "table";
  const [created, setCreated] = useState<Record<string, unknown> | null>(null);
  const [active, setActive] = useState("Overview");
  const [error, setError] = useState("");

  useEffect(() => {
    if (sessionId) {
      api.created(sessionId).then(setCreated).catch((e: Error) => setError(e.message));
    }
  }, [sessionId]);

  const rows = useMemo(() => {
    if (!created) return [];
    const candidate =
      created.sample_rows ??
      created.rows ??
      created.preview_rows ??
      created.sample_data ??
      created.data;
    return Array.isArray(candidate) ? (candidate as Record<string, unknown>[]) : [];
  }, [created]);

  const columns = useMemo(() => {
    if (Array.isArray(created?.columns)) return created.columns as Array<Record<string, unknown>>;
    return rows[0] ? Object.keys(rows[0]).map((name) => ({ name, type: "string" })) : [];
  }, [created, rows]);

  const path = `${catalog}.${schema}.${table}`;

  return (
    <div className="catalog-page">
      <div className="catalog-breadcrumb">
        <Link href="/catalog">Catalog</Link>
        <span>/</span>
        <span>{catalog}</span>
        <span>/</span>
        <span>{schema}</span>
      </div>
      <div className="catalog-title-row">
        <div>
          <div className="eyebrow">TABLE</div>
          <h1>{table}</h1>
          <p>{path}</p>
        </div>
        <div className="catalog-actions">
          <button className="secondary-button" type="button">
            Share
          </button>
          <button className="primary-button" type="button">
            Create
          </button>
        </div>
      </div>
      <div className="catalog-tabs">
        {["Overview", "Sample Data", "Details"].map((tab) => (
          <button
            className={active === tab ? "active" : ""}
            key={tab}
            onClick={() => setActive(tab)}
            type="button"
          >
            {tab}
          </button>
        ))}
      </div>
      {error ? <div className="error-banner">{error}</div> : null}
      {!created && !error ? (
        <div className="loading-state">
          <span className="spinner" />
          Loading table…
        </div>
      ) : (
        <>
          {active === "Overview" ? (
            <div className="catalog-content">
              <section className="catalog-main-card">
                <div className="card-head">
                  <h2>About this table</h2>
                  <button className="link-button" type="button">
                    Add comment
                  </button>
                </div>
                <p className="muted">
                  Created through Import Confidence Check with full-column conversion scanning.
                </p>
                <h2 className="schema-heading">Schema</h2>
                <table className="schema-table">
                  <thead>
                    <tr>
                      <th>Column name</th>
                      <th>Data type</th>
                      <th>Comment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {columns.map((column, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{text(column.name)}</strong>
                        </td>
                        <td>
                          <span className="type-chip">{text(column.type)}</span>
                        </td>
                        <td className="muted">-</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
              <aside className="catalog-details">
                <h2>Table details</h2>
                <dl>
                  <dt>Catalog</dt>
                  <dd>{catalog}</dd>
                  <dt>Schema</dt>
                  <dd>{schema}</dd>
                  <dt>Type</dt>
                  <dd>MANAGED</dd>
                  <dt>Format</dt>
                  <dd>DELTA</dd>
                  <dt>Owner</dt>
                  <dd>{text(created?.owner ?? "db")}</dd>
                  <dt>Rows</dt>
                  <dd>{text(created?.total_rows ?? created?.row_count ?? rows.length)}</dd>
                </dl>
              </aside>
            </div>
          ) : null}
          {active === "Sample Data" ? (
            <div className="sample-data-card">
              <div className="section-title-row">
                <div>
                  <h2>Sample Data</h2>
                  <p>Preview of the created table.</p>
                </div>
                <button className="secondary-button" type="button">
                  Refresh
                </button>
              </div>
              <div className="table-scroll">
                <table className="data-grid catalog-grid">
                  <thead>
                    <tr>
                      <th>#</th>
                      {columns.map((c, i) => (
                        <th key={i}>
                          {text(c.name)}
                          <small>{text(c.type)}</small>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr key={i}>
                        <td>{i + 1}</td>
                        {columns.map((c, j) => (
                          <td key={j}>{text(row[String(c.name)])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!rows.length ? (
                <div className="empty-data">No sample rows were returned by the backend.</div>
              ) : null}
            </div>
          ) : null}
          {active === "Details" ? (
            <div className="details-card">
              <h2>Properties</h2>
              <dl className="property-list">
                <dt>Full name</dt>
                <dd>{path}</dd>
                <dt>Table ID</dt>
                <dd>{text(created?.table_id ?? created?.id ?? "-")}</dd>
                <dt>Created at</dt>
                <dd>{text(created?.created_at ?? "Just now")}</dd>
                <dt>Created by</dt>
                <dd>{text(created?.created_by ?? created?.owner ?? "db")}</dd>
                <dt>Storage location</dt>
                <dd>{text(created?.location ?? "Managed by Databricks")}</dd>
              </dl>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

export default function CatalogTablePage() {
  return (
    <Suspense fallback={<div className="loading-state">Loading table…</div>}>
      <CatalogContent />
    </Suspense>
  );
}
