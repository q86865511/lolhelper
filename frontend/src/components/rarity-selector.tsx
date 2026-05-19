"use client";

import { useState } from "react";
import { AugmentTable, type AugmentMetaMap } from "@/components/augment-table";

type AugmentStat = {
  augment_id: number;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type Rarity = 1 | 2 | 3;

const RARITY_TABS: Array<{ value: Rarity; label: string; accent: string }> = [
  { value: 1, label: "銀 Silver", accent: "data-[active=true]:text-zinc-200 data-[active=true]:border-zinc-400" },
  { value: 2, label: "金 Gold", accent: "data-[active=true]:text-yellow-300 data-[active=true]:border-yellow-400" },
  { value: 3, label: "稜鏡 Prismatic", accent: "data-[active=true]:text-fuchsia-300 data-[active=true]:border-fuchsia-400" },
];

export function RaritySelector({
  augments,
  meta,
  totalChampionGames,
}: {
  augments: AugmentStat[];
  meta: AugmentMetaMap;
  totalChampionGames?: number | null;
}) {
  const [rarity, setRarity] = useState<Rarity>(2); // Gold is the most populous tier; good default

  const counts: Record<Rarity, number> = { 1: 0, 2: 0, 3: 0 };
  const grouped: Record<Rarity, AugmentStat[]> = { 1: [], 2: [], 3: [] };
  for (const a of augments) {
    const r = meta[a.augment_id]?.rarity;
    if (r === 1 || r === 2 || r === 3) {
      counts[r] += 1;
      grouped[r].push(a);
    }
  }

  return (
    <div>
      <div className="mb-3 flex gap-1 overflow-x-auto">
        {RARITY_TABS.map((t) => (
          <button
            key={t.value}
            type="button"
            data-active={rarity === t.value}
            onClick={() => setRarity(t.value)}
            className={`rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-text-muted transition hover:text-text data-[active=true]:bg-surface-2 ${t.accent}`}
          >
            {t.label}
            <span className="ml-1.5 text-[11px] text-text-dim">({counts[t.value]})</span>
          </button>
        ))}
      </div>
      <AugmentTable
        rows={grouped[rarity]}
        meta={meta}
        totalChampionGames={totalChampionGames}
        emptyMessage={`此英雄無達標的「${RARITY_TABS.find((t) => t.value === rarity)?.label}」augment 樣本`}
      />
    </div>
  );
}
