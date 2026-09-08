import Link from "next/link";

export default function AddDataPage() {
  return (
    <div className="page-content add-data-page">
      <header className="page-heading">
        <div>
          <h1>Add data</h1>
          <p>Upload a local file to create or modify a table.</p>
        </div>
      </header>

      <section aria-labelledby="files-heading">
        <h2 id="files-heading">Files</h2>
        <div className="file-cards">
          <Link href="/create-table/" className="feature-card feature-card-primary">
            <span className="feature-copy">
              <strong>Create or modify table</strong>
              <small>
                Upload CSV, JSON, or Excel to create a new table or replace an existing one.
              </small>
            </span>
            <span className="feature-chevron" aria-hidden="true">
              &gt;
            </span>
          </Link>
          <div className="feature-card muted-card" aria-disabled="true">
            <span className="feature-copy">
              <strong>Upload files to a volume</strong>
              <small>Not included in this prototype.</small>
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
