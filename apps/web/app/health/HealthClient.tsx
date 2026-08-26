"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CrossLinks } from "@/components/CrossLinks";
import { DemoBadge } from "@/components/DemoBadge";
import { FusionBanner } from "@/components/FusionBanner";
import { SeverityGauge } from "@/components/SeverityGauge";
import { StatusPill } from "@/components/StatusPill";
import { usePlot } from "@/lib/PlotContext";
import {
  ApiError,
  DEMO_PLOT_ID,
  getVisionReports,
  postVisionPredict,
  type VisionPrediction,
  type VisionReportRow,
} from "@/lib/api";
import { classLabelId, fmtNum, fmtTs, severityLabelId, severityTone } from "@/lib/format";

const SAMPLES = [
  { src: "/demo_samples/rice/rice-blast-demo.jpg", name: "rice-blast-demo.jpg", label: "Blast (field photo)", kind: "image/jpeg" },
  { src: "/demo_samples/rice/rice-blast-demo.svg", name: "rice-blast-demo.svg", label: "Blast (illustration)", kind: "image/svg+xml" },
  { src: "/demo_samples/rice/rice-brown-spot-demo.svg", name: "rice-brown-spot-demo.svg", label: "Brown spot (illustration)", kind: "image/svg+xml" },
  { src: "/demo_samples/rice/rice-tungro-demo.svg", name: "rice-tungro-demo.svg", label: "Tungro (illustration)", kind: "image/svg+xml" },
];

interface Rejection {
  code: string;
  detail: string;
}

function friendlyRejection(rej: Rejection): string {
  if (rej.code === "image_rejected") {
    return `The photo is unclear or not a leaf. Retake with the leaf filling the frame and even light. (${rej.detail})`;
  }
  if (rej.code === "low_confidence") {
    return `Model confidence is low. Take a closer photo with the lesion in sharp focus. (${rej.detail})`;
  }
  return rej.detail;
}

export function HealthClient() {
  const { refresh: refreshPlot } = usePlot();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<VisionPrediction | null>(null);
  const [rejection, setRejection] = useState<Rejection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reports, setReports] = useState<VisionReportRow[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refreshReports = useCallback(async () => {
    try {
      const res = await getVisionReports();
      setReports(res.reports);
    } catch {
      // non-fatal; list stays empty
    }
  }, []);

  useEffect(() => {
    refreshReports();
  }, [refreshReports]);

  const pickFile = useCallback(
    (f: File | null | undefined) => {
      if (!f) return;
      setFile(f);
      setResult(null);
      setRejection(null);
      setError(null);
      setPreviewUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(f);
      });
    },
    [],
  );

  const runPredict = useCallback(
    async (target: File) => {
      setBusy(true);
      setRejection(null);
      setError(null);
      try {
        const pred = await postVisionPredict({ file: target, plotId: DEMO_PLOT_ID, language: "en" });
        setResult(pred);
        refreshReports();
        refreshPlot();
      } catch (e) {
        setResult(null);
        if (e instanceof ApiError && (e.code === "image_rejected" || e.code === "low_confidence")) {
          setRejection({ code: e.code, detail: e.message });
        } else {
          setError(e instanceof Error ? e.message : "Check failed.");
        }
      } finally {
        setBusy(false);
      }
    },
    [refreshReports, refreshPlot],
  );

  const useSample = useCallback(
    async (sample: (typeof SAMPLES)[number]) => {
      try {
        const res = await fetch(sample.src);
        if (!res.ok) throw new Error(`Sample not found: ${sample.src}`);
        const blob = await res.blob();
        const f = new File([blob], sample.name, { type: sample.kind });
        pickFile(f);
        await runPredict(f);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load the sample.");
      }
    },
    [pickFile, runPredict],
  );

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  return (
    <div className="grid">
      <CrossLinks current="health" />
    <div className="grid grid--2" style={{ alignItems: "start" }}>
      {/* ── Upload workbench ── */}
      <div className="card" style={{ display: "grid", gap: 14 }}>
        <div
          className={`upload-dropzone${dragOver ? " is-drag" : ""}`}
          role="button"
          tabIndex={0}
          aria-label="Upload a leaf photo"
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <span>Leaf photo</span>
          <strong>Drop a photo here</strong>
          <small>or click to choose a file · JPG / PNG / WebP · non-leaf images are rejected</small>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => pickFile(e.target.files?.[0])}
          />
        </div>

        {previewUrl && (
          <figure className="photo-preview" style={{ margin: 0 }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={previewUrl} alt="Leaf photo preview" />
            <figcaption>{file?.name}</figcaption>
          </figure>
        )}

        <button
          type="button"
          className="button button--primary"
          disabled={!file || busy}
          onClick={() => file && runPredict(file)}
        >
          {busy ? "Checking…" : "Check leaf"}
        </button>

        <div>
          <h3 className="panel-heading" style={{ fontSize: "1.05rem", marginBottom: 8 }}>Try a sample (demo)</h3>
          <div className="sample-grid">
            {SAMPLES.map((s) => (
              <button key={s.src} type="button" className="sample-chip" disabled={busy} onClick={() => useSample(s)}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={s.src} alt="" />
                <span>{s.label}</span>
              </button>
            ))}
          </div>
        </div>

        {rejection && (
          <div className="callout callout--danger">
            <strong>Photo rejected.</strong>
            <p style={{ margin: "6px 0 0" }}>{friendlyRejection(rejection)}</p>
          </div>
        )}
        {error && (
          <div className="callout callout--warning">
            <strong>Something went wrong.</strong> {error}
          </div>
        )}
      </div>

      {/* ── Result + history ── */}
      <div style={{ display: "grid", gap: 18 }}>
        {result ? (
          <div className="card card--strong" style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: "1.45rem" }}>
                {result.class_label_en}
              </h3>
              <span style={{ display: "inline-flex", gap: 8 }}>
                {result.is_demo && <DemoBadge small />}
              </span>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, marginBottom: 6 }}>
                <span>Model confidence</span>
                <span>{fmtNum(result.confidence * 100)}%</span>
              </div>
              <div className="bar">
                <span style={{ width: `${Math.round(result.confidence * 100)}%` }} />
              </div>
            </div>

            <div className="grid grid--2" style={{ alignItems: "center" }}>
              <SeverityGauge label={result.severity} />
              <div>
                <span className="eyebrow">Advisory</span>
                <p style={{ margin: 0, lineHeight: 1.65 }}>
                  {result.advisory_en}
                </p>
                <div className="small muted mono" style={{ marginTop: 8 }}>{result.top_class}</div>
              </div>
            </div>

            {result.fusion && <FusionBanner fusion={result.fusion} />}

            <div className="small muted">
              Screening, not a diagnosis. Confirm with an extension officer.
            </div>
          </div>
        ) : (
          <div className="sub-panel muted">
            No result yet. Upload a photograph or pick a sample. Triage, severity, and fusion appear here.
          </div>
        )}

        <div>
          <h3 className="panel-heading" style={{ fontSize: "1.15rem", marginBottom: 10 }}>Recent reports</h3>
          {reports.length === 0 ? (
            <p className="muted small">No reports yet.</p>
          ) : (
            <div className="report-list">
              {reports.slice(0, 6).map((r) => (
                <div key={r.report_id} className="report-row">
                  <strong>{classLabelId(r.top_class)}</strong>
                  <span className="muted small">{fmtNum(r.confidence * 100)}%</span>
                  <StatusPill label={severityLabelId(r.severity)} tone={severityTone(r.severity) === "urgent" ? "danger" : severityTone(r.severity) === "high" ? "alert" : "default"} />
                  {r.is_demo && <DemoBadge small />}
                  <span className="spacer" />
                  <span className="muted small">{fmtTs(r.ts)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
    </div>
  );
}
