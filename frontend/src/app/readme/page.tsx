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
        Prototype only. Do not upload real or sensitive data. Use fake test files or the built-in
        samples.
      </div>

      <section className="readme-section" aria-labelledby="howto-heading">
        <h2 id="howto-heading">How to use</h2>
        <ol className="readme-steps">
          <li>
            <span className="readme-step-num" aria-hidden="true">
              1
            </span>
            <span>
              Open <Link href="/">Data Ingestion</Link>, then{" "}
              <Link href="/create-table">Create or modify table</Link>.
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
              Open <Link href="/catalog">Catalog</Link> to see tables from this session.
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
