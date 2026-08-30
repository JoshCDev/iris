"use client";

import { useMemo, useState } from "react";
import type { Reading } from "@/lib/api";
import { fmtNum, fmtTs } from "@/lib/format";

const W = 920;
const H = 300;
const PAD_L = 48;
const PAD_R = 16;
const PAD_T = 16;
const PAD_B = 30;
const TICK_PX = 12.5;

function niceDomain(min: number, max: number): [number, number] {
  // Always include the agronomic band (+5 flooded … −15 trigger) when the data
  // fits; pad beyond it only when readings genuinely leave the band.
  let lo = Math.min(-17, Math.floor(min) - 1);
  let hi = Math.max(7, Math.ceil(max) + 1);
  lo = Math.max(lo, -40);
  hi = Math.min(hi, 20);
  return [lo, hi];
}

export function LevelChart({
  readings,
  compact = false,
  dataKind,
}: {
  readings: Reading[];
  compact?: boolean;
  dataKind?: "manual" | "sensor" | "simulation" | "other" | null;
}) {
  const [hover, setHover] = useState<number | null>(null);

  const geo = useMemo(() => {
    if (readings.length < 2) return null;
    const t0 = new Date(readings[0].ts).getTime();
    const tN = new Date(readings[readings.length - 1].ts).getTime();
    const span = Math.max(tN - t0, 1);
    const levels = readings.map((r) => r.level_cm);
    const [yMin, yMax] = niceDomain(Math.min(...levels), Math.max(...levels));
    const yPos = (v: number) =>
      PAD_T + ((yMax - v) / (yMax - yMin)) * (H - PAD_T - PAD_B);
    const pts = readings.map((r) => {
      const x = PAD_L + ((new Date(r.ts).getTime() - t0) / span) * (W - PAD_L - PAD_R);
      return { x, y: yPos(r.level_cm), level: r.level_cm, ts: r.ts };
    });
    const line = pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const area = `${PAD_L},${yPos(yMin)} ${line} ${pts[pts.length - 1].x.toFixed(1)},${yPos(yMin)}`;
    return { t0, span, yMin, yMax, yPos, pts, line, area, last: pts[pts.length - 1] };
  }, [readings]);

  if (!geo) {
    return (
      <div className="level-chart muted" style={{ padding: "24px 4px" }}>
        Not enough readings for a chart.
      </div>
    );
  }

  const { yPos, pts, line, area, last, yMin, yMax } = geo;
  const gridVals: number[] = [];
  for (let v = Math.ceil(yMax); v >= Math.floor(yMin); v -= 5) gridVals.push(v);
  if (!gridVals.includes(-15)) gridVals.push(-15);

  const onMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * W;
    let best = 0;
    let bestD = Infinity;
    pts.forEach((p, i) => {
      const d = Math.abs(p.x - x);
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    });
    setHover(best);
  };

  const hp = hover !== null ? pts[hover] : null;

  const levels = readings.map((r) => r.level_cm);
  const min = Math.min(...levels);
  const max = Math.max(...levels);

  const kindLabel: Record<string, string> = {
    manual: "manual observation",
    sensor: "sensor",
    simulation: "simulation",
  };
  // Only claim a data kind when the payload explicitly names one;
  // unknown/"other" sources (e.g. legacy seeded readings) render as before.
  const dataSourceLabel =
    dataKind && dataKind in kindLabel ? kindLabel[dataKind] : null;

  return (
    <figure
      className="level-chart"
      style={{ margin: 0, position: "relative" }}
      aria-labelledby="level-chart-title"
    >
      <h3 id="level-chart-title" className="sr-only">Water level over time</h3>
      {dataSourceLabel && (
        <p className="small muted" style={{ margin: "0 0 6px" }}>
          Data source: {dataSourceLabel}
        </p>
      )}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Plot water-level chart"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {/* flooded target band +5…0 cm */}
        <rect
          x={PAD_L}
          y={yPos(5)}
          width={W - PAD_L - PAD_R}
          height={yPos(0) - yPos(5)}
          fill="rgba(45,95,115,0.16)"
        />
        {/* gridlines */}
        {gridVals.map((v) => (
          <g key={v}>
            <line
              x1={PAD_L}
              x2={W - PAD_R}
              y1={yPos(v)}
              y2={yPos(v)}
              stroke={v === -15 ? "rgba(23,33,27,0.04)" : "rgba(23,33,27,0.08)"}
              strokeWidth="1"
            />
            <text x={PAD_L - 8} y={yPos(v) + 4} textAnchor="end" fontSize={TICK_PX} fill="#5d675f">
              {v > 0 ? `+${v}` : v}
            </text>
          </g>
        ))}
        {/* AWD trigger −15 cm */}
        <line
          x1={PAD_L}
          x2={W - PAD_R}
          y1={yPos(-15)}
          y2={yPos(-15)}
          stroke="#b84b3c"
          strokeWidth="1.6"
          strokeDasharray="7 5"
        />
        {!compact && (
          <text x={W - PAD_R - 4} y={yPos(-15) - 6} textAnchor="end" fontSize={TICK_PX} fontWeight="800" fill="#b84b3c">
            AWD trigger −15 cm
          </text>
        )}
        {/* area + trace */}
        <polygon points={area} fill="rgba(95,159,62,0.13)" />
        <polyline points={line} fill="none" stroke="#2f6845" strokeWidth="2.4" strokeLinejoin="round" />
        {hp && (
          <g>
            <line x1={hp.x} x2={hp.x} y1={PAD_T} y2={H - PAD_B} stroke="rgba(23,33,27,0.25)" strokeWidth="1" />
            <circle cx={hp.x} cy={hp.y} r="4" fill="#1f3d2b" stroke="#fbfaf4" strokeWidth="2" />
          </g>
        )}
        {!compact && hover === null && (
          <>
            <circle cx={last.x} cy={last.y} r="4.5" fill="#1f3d2b" stroke="#fbfaf4" strokeWidth="2" />
            <text x={last.x - 6} y={last.y - 10} textAnchor="end" fontSize={TICK_PX} fontWeight="800" fill="#10231a">
              {fmtNum(last.level)} cm
            </text>
          </>
        )}
        {/* x axis time labels (first / middle / last) */}
        {!compact && (
          <>
            <text x={PAD_L} y={H - 8} fontSize={TICK_PX} fill="#5d675f">{fmtTs(readings[0].ts)}</text>
            <text x={(PAD_L + W - PAD_R) / 2} y={H - 8} textAnchor="middle" fontSize={TICK_PX} fill="#5d675f">
              {fmtTs(readings[Math.floor(readings.length / 2)].ts)}
            </text>
            <text x={W - PAD_R} y={H - 8} textAnchor="end" fontSize={TICK_PX} fill="#5d675f">
              {fmtTs(readings[readings.length - 1].ts)}
            </text>
          </>
        )}
      </svg>
      {hp && (
        <div
          className="chart-tip"
          style={{
            left: `${(hp.x / W) * 100}%`,
            top: 0,
            transform: `translateX(${hp.x > W * 0.75 ? "-105%" : hp.x < W * 0.25 ? "5%" : "-50%"})`,
          }}
        >
          <strong>{fmtNum(hp.level)} cm</strong> · {fmtTs(hp.ts)}
        </div>
      )}
      <p className="small" style={{ margin: "6px 0 8px" }}>
        Latest {fmtNum(last.level)} cm · minimum {fmtNum(min)} · maximum {fmtNum(max)} · trigger −15 cm · {fmtTs(readings[0].ts)} → {fmtTs(readings[readings.length - 1].ts)}
      </p>
      <details className="data-table">
        <summary>Data table</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">Time</th>
              <th scope="col">Water level (cm)</th>
            </tr>
          </thead>
          <tbody>
            {readings.map((r) => (
              <tr key={r.ts}>
                <td>{fmtTs(r.ts)}</td>
                <td>{fmtNum(r.level_cm)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
      <figcaption className="chart-legend">
        <span><i style={{ background: "#2f6845" }} />water level (cm)</span>
        <span><i style={{ background: "rgba(45,95,115,0.35)" }} />flood band +5…0 cm (required at flowering)</span>
        <span><i style={{ background: "#b84b3c", height: 3 }} />AWD irrigation trigger</span>
      </figcaption>
    </figure>
  );
}
