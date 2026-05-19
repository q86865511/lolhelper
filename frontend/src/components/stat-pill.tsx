export function StatPill({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: React.ReactNode;
  emphasize?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-xs">
      <span className="text-text-dim">{label}</span>
      <span className={emphasize ? "font-semibold text-text" : "text-text"}>{value}</span>
    </div>
  );
}
