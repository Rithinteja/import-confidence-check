"use client";

import { api } from "@/lib/api";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { DragEvent, Suspense, useEffect, useRef, useState } from "react";

type Sample = Record<string, unknown>;

const FEATURED_SAMPLE_ID = "after-preview";

function fileBadge(filename: string): string {
  const ext = filename.split(".").pop()?.toUpperCase() || "FILE";
  if (ext === "XLSX" || ext === "XLS") return "XLSX";
  if (ext === "JSON") return "JSON";
  if (ext === "TSV") return "TSV";
  return "CSV";
}

function CreateTableContent() {
  const router = useRouter();
  const search = useSearchParams();
  const inputRef = useRef<HTMLInputElement>(null);
  const autoSample = search.get("sample");
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const autoStarted = useRef(false);

  useEffect(() => {
    api.samples().then(setSamples).catch(() => setSamples([]));
  }, []);

  const finish = (sessionId: string) =>
    router.push(`/create-table/preview?session=${encodeURIComponent(sessionId)}`);

  async function upload(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      finish((await api.upload(file)).session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setBusy(false);
    }
  }

  async function chooseSample(id: string) {
    setBusy(true);
    setError("");
    try {
      finish((await api.loadSample(id)).session_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load sample");
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!autoSample || autoStarted.current) return;
    autoStarted.current = true;
    void chooseSample(autoSample);
    // intentionally once on mount for ?sample=
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSample]);

  function drop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    void upload(e.dataTransfer.files[0]);
  }

  const orderedSamples = [...samples].sort((a, b) => {
    const aId = String(a.id ?? "");
    const bId = String(b.id ?? "");
    if (aId === FEATURED_SAMPLE_ID) return -1;
    if (bId === FEATURED_SAMPLE_ID) return 1;
    return 0;
  });

  return (
    <div className="page-content upload-page dbx-upload">
      <div className="upload-top-row">
        <div>
          <div className="breadcrumb">
            <Link href="/">Add data</Link>
            <span>/</span>
          </div>
          <h1>Create table from file</h1>
        </div>
        <div className="warehouse-chip" title="Prototype compute selector">
          <span className="status-dot" />
          Serverless Starter Warehouse
        </div>
      </div>

      <div className="source-tabs square-tabs">
        <button className="source-tab active" type="button">
          File upload
        </button>
        <button className="source-tab" type="button" disabled>
          S3
        </button>
      </div>

      <div
        className={`drop-zone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={drop}
      >
        <p className="drop-title">
          {busy ? (
            "Preparing your preview…"
          ) : (
            <>
              Drop one or more files here, or{" "}
              <button
                type="button"
                className="link-button inline-link"
                disabled={busy}
                onClick={() => inputRef.current?.click()}
              >
                browse
              </button>
            </>
          )}
        </p>
        <p className="drop-meta">Maximum upload size: 10 MB in this prototype.</p>
        <p className="drop-meta">
          Supported file formats: CSV, TSV, JSON, or Excel. Any valid test file works. Parsing and
          Import Confidence Check run on the uploaded values. Optional short risk notes can appear when AI is enabled.
        </p>
        <input
          ref={inputRef}
          hidden
          type="file"
          accept=".csv,.tsv,.json,.xlsx,.xls"
          onChange={(e) => void upload(e.target.files?.[0])}
        />
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      <p className="volume-note">
        For larger files or non-tabular datasets, upload to a Volume in Unity Catalog. That path is
        not in this prototype.
      </p>

      <section className="samples">
        <div className="section-title-row">
          <div>
            <h2>Try a sample file</h2>
            <p>Same engine as browse or drag-and-drop. Results are scanned live, not hardcoded.</p>
          </div>
        </div>
        <div className="sample-list">
          {orderedSamples.length ? (
            orderedSamples.map((sample, i) => {
              const id = String(sample.id ?? i);
              const filename = String(sample.filename ?? "");
              const name = String(sample.label ?? filename);
              const featured = id === FEATURED_SAMPLE_ID;
              return (
                <div className={`sample-row ${featured ? "sample-row-featured" : ""}`} key={id}>
                  <span className="file-type">{fileBadge(filename)}</span>
                  <span className="sample-copy">
                    <strong className="sample-title">{name}</strong>
                    <small className="sample-desc">{String(sample.description ?? "")}</small>
                  </span>
                  <span className="sample-actions">
                    <a
                      className="sample-download"
                      href={api.sampleFileUrl(id)}
                      download={filename || undefined}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Download
                    </a>
                    <button
                      disabled={busy}
                      className={`sample-action ${featured ? "sample-action-primary" : ""}`}
                      type="button"
                      onClick={() => void chooseSample(id)}
                    >
                      Try this file
                    </button>
                  </span>
                </div>
              );
            })
          ) : (
            <div className="samples-loading">Loading samples…</div>
          )}
        </div>
      </section>
    </div>
  );
}

export default function CreateTablePage() {
  return (
    <Suspense fallback={<div className="page-content loading-state">Loading…</div>}>
      <CreateTableContent />
    </Suspense>
  );
}
