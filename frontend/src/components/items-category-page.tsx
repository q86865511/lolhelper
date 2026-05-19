"use client";

import { useState, useMemo } from "react";
import { ItemTable, type ItemMetaMap } from "@/components/item-table";

type ItemStat = {
  item_id: number;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type Bucket = {
  category: "boots" | "prismatic" | "core";
  items: ItemStat[];
  totalPlayerGames: number;
};

const TABS: Array<{
  value: "boots" | "prismatic" | "core";
  label: string;
  hint: string;
}> = [
  { value: "core", label: "核心裝備", hint: "完整裝備(1000 金以上)" },
  { value: "prismatic", label: "稜鏡裝備", hint: "由「稜鏡能力值鐵砧」augment 或事件抽到(2750 金以上)" },
  { value: "boots", label: "鞋子", hint: "移動鞋類" },
];

export function ItemsCategoryPage({
  buckets,
  meta,
}: {
  buckets: Bucket[];
  meta: ItemMetaMap;
}) {
  const [cat, setCat] = useState<"boots" | "prismatic" | "core">("core");
  const current = useMemo(
    () => buckets.find((b) => b.category === cat),
    [buckets, cat],
  );
  const tabInfo = TABS.find((t) => t.value === cat);

  return (
    <>
      <div className="mt-5 flex flex-wrap gap-1">
        {TABS.map((t) => {
          const b = buckets.find((x) => x.category === t.value);
          return (
            <button
              key={t.value}
              type="button"
              onClick={() => setCat(t.value)}
              className={`rounded-md border border-border bg-surface px-3 py-1.5 text-sm transition hover:text-text ${
                cat === t.value ? "bg-surface-2 text-text" : "text-text-muted"
              }`}
            >
              {t.label}
              <span className="ml-1.5 text-[11px] text-text-dim">
                ({b?.items.length ?? 0})
              </span>
            </button>
          );
        })}
      </div>

      {tabInfo && (
        <p className="mt-3 text-xs text-text-dim">
          {tabInfo.hint} · 全英雄跨對戰聚合,Wilson 下界排序。
        </p>
      )}

      <div className="mt-4">
        <ItemTable
          rows={current?.items ?? []}
          meta={meta}
          totalChampionGames={current?.totalPlayerGames ?? null}
          emptyMessage={`此類別尚無達 30 場樣本的裝備`}
        />
      </div>
    </>
  );
}
