type Rarity = 1 | 2 | 3 | null;

const rarityMap: Record<Exclude<Rarity, null>, { label: string; cls: string }> = {
  1: { label: "Silver", cls: "border-zinc-500/40 bg-zinc-500/15 text-zinc-300" },
  2: { label: "Gold", cls: "border-yellow-500/40 bg-yellow-500/15 text-yellow-300" },
  3: { label: "Prismatic", cls: "border-fuchsia-500/40 bg-fuchsia-500/15 text-fuchsia-300" },
};

export function RarityTag({ rarity }: { rarity: Rarity }) {
  if (!rarity) return <span className="text-text-dim">—</span>;
  const r = rarityMap[rarity];
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium ${r.cls}`}>
      {r.label}
    </span>
  );
}
