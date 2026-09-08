import Link from "next/link";

export default function ReadmePage() {
  return (
    <div className="page-content readme-page">
      <header className="page-heading">
        <div>
          <h1>Home</h1>
          <p>What this Import Confidence Check prototype does, and how to try it.</p>
        </div>
      </header>

      <div className="readme-banner" role="status">
        <strong>Prototype only. Do not upload real or sensitive data.</strong>
        <span>
          Use fake test files or the built-in samples. This is a conversion-risk demo for
          Databricks-style file upload, not a production system.
        </span>
      </div>

      <section className="readme-section demo-cta-card">
        <h2>Recommended first</h2>
        <p>
          The preview shows the first 50 rows. This 75-row sample looks clean in the grid, then
          Import Confidence Check finds risks starting at row 51. One click loads it.
        </p>
        <p className="demo-cta-actions">
          <Link
            className="primary-button"
            href="/create-table/?sample=after-preview"
          >
            Try the 75-row sample
          </Link>
          <Link className="secondary-button" href="/create-table/">
            Browse all samples
          </Link>
        </p>
      </section>

      <section className="readme-section">
        <h2>How to use the site</h2>
        <ol className="readme-steps">
          <li>
            Open <Link href="/">Data Ingestion</Link> and choose{" "}
            <Link href="/create-table">Create or modify table</Link>.
          </li>
          <li>
            Upload a CSV, TSV, JSON, or Excel <em>test</em> file, or click{" "}
            <strong>Use sample</strong> under Try a sample file.
          </li>
          <li>
            Check inferred types and Import Confidence Check risks. Apply fixes when you want (for
            example keep IDs as string), then create the table.
          </li>
          <li>
            Open <Link href="/catalog">Catalog</Link> to see tables created in this session.
          </li>
        </ol>
        <p className="muted">
          Sample files also have a <strong>Download</strong> link so you can inspect the file
          locally before importing.
        </p>
      </section>

      <section className="readme-section">
        <h2>What is running</h2>
        <ul className="readme-list">
          <li>
            <strong>File checker.</strong> Uploads and samples are parsed, types are inferred, and
            every row is scanned for silent conversion risks: leading-zero loss, bad dates, decimal
            rounding, issues past the preview window, and similar cases. Findings come from the
            scanner, not canned screenshots.
          </li>
          <li>
            <strong>Postgres.</strong> Import sessions and created-table metadata live in a real
            database (Neon Postgres on the public deploy; SQLite locally if{" "}
            <code>DATABASE_URL</code> is unset). Catalog reads from that store.
          </li>
          <li>
            <strong>Groq.</strong> Explains risks and writes short import summaries when configured.
            Detection still runs if Groq is down; the UI falls back to built-in text.
          </li>
        </ul>
      </section>
    </div>
  );
}
