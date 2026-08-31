"use client";

import { useCallback, useRef, useState } from "react";
import { CrossLinks } from "@/components/CrossLinks";
import { DemoBadge } from "@/components/DemoBadge";
import { SeverityGauge } from "@/components/SeverityGauge";
import { usePlot } from "@/lib/PlotContext";
import { ApiError } from "@/lib/api";
import { postV1LeafAssessment, type LeafAssessment } from "@/lib/api/v1";
import { classLabelId, fmtNum } from "@/lib/format";

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
  const { refresh: refreshPlot, activePlotId } = usePlot();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<LeafAssessment | null>(null);
  const [rejection, setRejection] = useState<Rejection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      if (activePlotId === null) return;
      setBusy(true);
      setRejection(null);
      setError(null);
      try {
        const pred = await postV1LeafAssessment(activePlotId, target);
        setResult(pred);
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
    [activePlotId, refreshPlot],
  );

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    pickFile(e.dataTransfer.files?.[0]);
  };

  // Start over: drop the current photo + result so a fresh photo can be picked.
  const resetForNewPhoto = () => {
    setFile(null);
    setResult(null);
    setRejection(null);
    setError(null);
    setPreviewUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
  };

  // "Check another leaf": reset, then reopen the native file picker once the
  // dropzone has re-rendered (the input is inside the now-remounted dropzone).
  const checkAnotherLeaf = () => {
    resetForNewPhoto();
    requestAnimationFrame(() => fileInputRef.current?.click());
  };

  return (
    <div className="grid">
      <CrossLinks current="health" />
    <div className="grid grid--2" style={{ alignItems: "start" }}>
      {/* ── Upload workbench ── */}
      <div className="card" style={{ display: "grid", gap: 14 }}>
        {!file && (
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
        )}

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
          onClick={() => (result ? checkAnotherLeaf() : file && runPredict(file))}
        >
          {busy ? "Checking…" : result ? "Check another leaf" : "Check leaf"}
        </button>

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

      {/* ── Result ── */}
      <div style={{ display: "grid", gap: 18 }}>
        {result ? (
          <div className="card card--strong" style={{ display: "grid", gap: 14 }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: "1.45rem" }}>
                {result.class_label_en ?? classLabelId(result.class ?? "none")}
              </h3>
              <span style={{ display: "inline-flex", gap: 8 }}>
                {result.demo && <DemoBadge small />}
              </span>
            </div>

            {result.confidence !== null && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, marginBottom: 6 }}>
                  <span>Model confidence</span>
                  <span>{fmtNum(result.confidence * 100)}%</span>
                </div>
                <div className="bar">
                  <span style={{ width: `${Math.round(result.confidence * 100)}%` }} />
                </div>
              </div>
            )}

            <div className="grid grid--2" style={{ alignItems: "center" }}>
              <SeverityGauge label={result.severity ?? "n/a"} />
              <div>
                <span className="eyebrow">Screening result</span>
                <p style={{ margin: 0, lineHeight: 1.65 }}>
                  {result.class_label_en ?? classLabelId(result.class ?? "none")}
                </p>
                <div className="small muted mono" style={{ marginTop: 8 }}>{result.class}</div>
              </div>
            </div>

            <div className="small muted">
              {result.disclaimer ??
                "Screening, not a diagnosis. Confirm with an extension officer."}
            </div>
          </div>
        ) : (
          <div className="sub-panel muted">
            No result yet. Upload a photograph. Triage and severity appear here.
          </div>
        )}
      </div>
    </div>
    </div>
  );
}
