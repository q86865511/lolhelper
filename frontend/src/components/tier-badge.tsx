type Tier = "S" | "A" | "B" | "C" | "D" | null;

const tierColor: Record<Exclude<Tier, null>, string> = {
  S: "bg-red-500 text-white",
  A: "bg-orange-500 text-white",
  B: "bg-yellow-500 text-zinc-900",
  C: "bg-blue-500 text-white",
  D: "bg-zinc-500 text-white",
};

export function TierBadge({ tier, size = "md" }: { tier: Tier; size?: "sm" | "md" }) {
  const dim = size === "sm" ? "h-5 w-5 text-[10px]" : "h-7 w-7 text-xs";
  if (!tier) {
    return (
      <span className={`inline-flex items-center justify-center rounded border border-border text-text-dim ${dim}`}>
        —
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center justify-center rounded font-bold ${dim} ${tierColor[tier]}`}
    >
      {tier}
    </span>
  );
}
