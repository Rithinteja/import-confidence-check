import Link from "next/link";

export default function ReadmePage() {
  return (
    <div className="page-content readme-page">
      <header className="page-heading">
        <div>
          <h1>Home</h1>
          <p>Import Confidence Check prototype. How it works and how to try it.</p>
        </div>
      </header>

      <div className="readme-banner" role="status">
        <strong>Prototype only. Do not upload real or sensitive data.</strong>
        <span>Use fake test files or the built-in samples.</span>
      </div>

      <section className="readme-section demo-cta-card">
        <h2>Recommended first</h2>
        <p>
          Preview shows 50 rows. This 75-row file looks clean there, then Confidence Check finds
          risks from row 51 on.
        </p>
        <p className="demo-cta-actions">
          <Link className="primary-button" href="/create-table/?sample=after-preview">
            Try this file
          </Link>
          <Link className="secondary-button" href="/create-table/">
            Browse all samples
          </Link>
        </p>
      </section>

      <section className="readme-section">
        <h2>How to use</h2>
        <ol className="readme-steps">
          <li>
            Open <Link href="/">Data Ingestion</Link>, then{" "}
            <Link href="/create-table">Create or modify table</Link>.
          </li>
          <li>
            Upload a test CSV, TSV, JSON, or Excel file, or pick a sample with{" "}
            <strong>Try this file</strong>.
          </li>
          <li>Review risks, apply fixes if you want, then create the table.</li>
          <li>
            Open <Link href="/catalog">Catalog</Link> to see tables from this session.
          </li>
        </ol>
        <p className="muted">Samples also have a Download link if you want the file on disk first.</p>
      </section>

      <section className="readme-section">
        <h2>What is running</h2>
        <ul className="readme-list">
          <li>
            <strong>File checker.</strong> Parses the file, infers types, and scans every row for
            silent conversion risks.
          </li>
          <li>
            <strong>Database.</strong> Sessions and created tables are stored in Postgres. Catalog
            reads from that store.
          </li>
          <li>
            <strong>Groq.</strong> Optional short explanations of detected risks. Scanning still
            works if Groq is off.
          </li>
        </ul>
      </section>
    </div>
  );
}
