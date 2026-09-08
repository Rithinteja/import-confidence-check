import Link from "next/link";

export default function HomePage() {
  return (
    <div className="page-content readme-page">
      <header className="page-heading">
        <div>
          <h1>Home</h1>
          <p>What this Import Confidence Check prototype does, and how to try it.</p>
        </div>
      </header>

      <div className="readme-banner" role="status">
        Prototype only. Do not upload real or sensitive data. Use fake test files or the built-in
        samples.
      </div>

      <section className="readme-section" aria-labelledby="problem-heading">
        <h2 id="problem-heading">The problem</h2>
        <p className="readme-lead readme-lead-wide">
          Today, Databricks suggests column types and shows a 50-row preview, but does not summarize
          which source values will change during conversion. Users must compare the preview with the
          original file themselves and may not discover problems until after creating the table.
          Import Confidence Check scans the full file, identifies confirmed value changes, explains
          their impact, and recommends a fix before table creation.
        </p>
      </section>

      <section className="readme-section" aria-labelledby="howto-heading">
        <h2 id="howto-heading">How to use</h2>
        <ol className="readme-steps">
          <li>
            <span className="readme-step-num" aria-hidden="true">
              1
            </span>
            <span>
              Open <Link href="/add-data/">Data Ingestion</Link>, then{" "}
              <Link href="/create-table/">Create or modify table</Link>.
            </span>
          </li>
          <li>
            <span className="readme-step-num" aria-hidden="true">
              2
            </span>
            <span>
              Upload a test CSV, TSV, JSON, or Excel file, or pick a sample with{" "}
              <strong>Try this file</strong>.
            </span>
          </li>
          <li>
            <span className="readme-step-num" aria-hidden="true">
              3
            </span>
            <span>Review risks, apply fixes if you want, then create the table.</span>
          </li>
          <li>
            <span className="readme-step-num" aria-hidden="true">
              4
            </span>
            <span>
              Open <Link href="/catalog/">Catalog</Link> to see tables from this session.
            </span>
          </li>
        </ol>
        <p className="readme-footnote">
          Samples also have a Download link if you want the file on disk first.
        </p>
      </section>

      <section className="readme-section" aria-labelledby="running-heading">
        <h2 id="running-heading">What is running</h2>
        <dl className="readme-defs">
          <div>
            <dt>File checker</dt>
            <dd>Parses the file, infers types, and scans every row for silent conversion risks.</dd>
          </div>
          <div>
            <dt>Database</dt>
            <dd>Sessions and created tables are stored in Postgres. Catalog reads from that store.</dd>
          </div>
          <div>
            <dt>Groq</dt>
            <dd>Optional short explanations of detected risks. Scanning still works if Groq is off.</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
