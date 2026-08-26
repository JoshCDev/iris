// Honesty rule: any seeded/demo-derived record carries this badge.
export function DemoBadge({ small = false }: { small?: boolean }) {
  return (
    <span className={small ? "demo-badge demo-badge--small" : "demo-badge"}>
      Demo data
    </span>
  );
}
