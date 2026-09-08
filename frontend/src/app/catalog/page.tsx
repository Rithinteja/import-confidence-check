"use client";

import { api } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

type TableMeta = {
  session_id: string;
  catalog: string;
  schema: string;
  table_name: string;
  created_at: string;
  total_rows: number;
  size_label: string;
  owner: string;
};

export default function CatalogIndexPage() {
  const [tables, setTables] = useState<TableMeta[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .tables()
      .then(setTables)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="catalog-index page-content">
      <div className="catalog-layout">
        <aside className="catalog-tree">
          <div className="catalog-tree-head">
            <h2>Catalog</h2>
            <div className="warehouse-chip compact">
              <span className="status-dot" />
              Serverless Starter Warehouse
            </div>
          </div>
          <div className="tree-group">
            <div className="tree-label">My organization</div>
            <div className="tree-item">dbacademy</div>
            <div className="tree-item nested">default</div>
            <div className="tree-item nested strong">Tables ({tables.length})</div>
            {tables.map((t) => (
              <Link
                key={t.session_id}
                className="tree-item nested deep"
                title={t.table_name}
                href={`/catalog/table?catalog=${encodeURIComponent(t.catalog)}&schema=${encodeURIComponent(t.schema)}&table=${encodeURIComponent(t.table_name)}&session=${encodeURIComponent(t.session_id)}`}
              >
                {t.table_name}
              </Link>
            ))}
          </div>
        </aside>

        <section className="catalog-index-main">
          <div className="breadcrumb">
            <span>Catalog Explorer</span>
            <span>/</span>
            <span>dbacademy</span>
            <span>/</span>
            <span>default</span>
          </div>
          <h1>Tables</h1>
          <p className="muted">
            Tables created in this prototype session appear here after Import Confidence Check.
          </p>

          {loading ? <div className="loading-state">Loading tables…</div> : null}
          {error ? <div className="error-banner">{error}</div> : null}

          {!loading && !tables.length ? (
            <div className="empty-catalog">
              <p>No tables yet.</p>
              <Link className="primary-button" href="/create-table">
                Create table from file
              </Link>
            </div>
          ) : null}

          {tables.length ? (
            <table className="schema-table catalog-list-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Catalog</th>
                  <th>Schema</th>
                  <th>Rows</th>
                  <th>Size</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {tables.map((t) => (
                  <tr key={t.session_id}>
                    <td>
                        <Link
                        className="table-name-link"
                        title={t.table_name}
                        href={`/catalog/table?catalog=${encodeURIComponent(t.catalog)}&schema=${encodeURIComponent(t.schema)}&table=${encodeURIComponent(t.table_name)}&session=${encodeURIComponent(t.session_id)}`}
                      >
                        {t.table_name}
                      </Link>
                    </td>
                    <td>{t.catalog}</td>
                    <td>{t.schema}</td>
                    <td>{t.total_rows}</td>
                    <td>{t.size_label}</td>
                    <td>{new Date(t.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </section>
      </div>
    </div>
  );
}
