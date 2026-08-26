import { SEVERITY_PCT, severityLabelId, severityTone } from "@/lib/format";

const RADIUS = 46;
const CIRC = 2 * Math.PI * RADIUS;

// Qualitative severity gauge. The backend only returns a bucket label
// (Low ≤25 / Moderate ≤50 / High ≤75 / Urgent >75); the needle sits at the
// bucket bound - no invented precision.
export function SeverityGauge({ label }: { label: string }) {
  const tone = severityTone(label);
  const pct = SEVERITY_PCT[label] ?? 50;
  const offset = CIRC * (1 - pct / 100);
  return (
    <div className="severity-gauge">
      <div className="severity-gauge__dial">
        <svg viewBox="0 0 116 116" width="116" height="116" aria-hidden="true">
          <circle cx="58" cy="58" r={RADIUS} fill="none" stroke="rgba(23,33,27,0.1)" strokeWidth="10" />
          <circle
            cx="58"
            cy="58"
            r={RADIUS}
            fill="none"
            className={`sev-${tone}`}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={CIRC}
            strokeDashoffset={offset}
          />
        </svg>
        <div className={`severity-gauge__value txt-${tone}`}>{severityLabelId(label)}</div>
      </div>
      <div className={`txt-${tone}`} style={{ fontWeight: 800, fontSize: "0.85rem" }}>
        Severity: {severityLabelId(label)}
      </div>
    </div>
  );
}
