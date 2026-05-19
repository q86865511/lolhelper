"use client";

import { useState } from "react";
import { ItemTable, type ItemMetaMap } from "@/components/item-table";

type ItemStat = {
  item_id: number;
  games: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

/** Items table with a default-collapsed "show more" toggle (e.g. for prismatic). */
export function ExpandableItemTable({
  rows,
  meta,
  defaultShow = 5,
  totalChampionGames,
  emptyMessage,
}: {
  rows: ItemStat[];
  meta: ItemMetaMap;
  defaultShow?: number;
  totalChampionGames?: number | null;
  emptyMessage?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows : rows.slice(0, defaultShow);
  const hidden = rows.length - visible.length;
  return (
    <>
      <ItemTable
        rows={visible}
        meta={meta}
        totalChampionGames={totalChampionGames}
        emptyMessage={emptyMessage}
      />
      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-xs text-text-muted transition hover:border-border-strong hover:text-text"
        >
          顯示更多({hidden} 項) ▾
        </button>
      )}
      {expanded && rows.length > defaultShow && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="mt-2 w-full rounded-md border border-border bg-surface px-3 py-2 text-xs text-text-muted transition hover:border-border-strong hover:text-text"
        >
          收合 ▴
        </button>
      )}
    </>
  );
}
