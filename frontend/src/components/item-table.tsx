"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { cdragonAsset } from "@/lib/cdragon";
import { cleanLolText, truncate } from "@/lib/lol-text";
import { formatNumber, formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";
import { HoverTooltip } from "@/components/hover-tooltip";

type ItemStat = {
  item_id: number;
  games: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type ItemMeta = {
  id: number;
  name: string;
  description: string | null;
  gold: number | null;
  icon_path: string | null;
};

type SortKey = "win_rate" | "pick_rate" | "games" | "gold";
const SORT_COLS: Record<SortKey, { label: string; dir: "asc" | "desc" }> = {
  win_rate: { label: "勝率", dir: "desc" },
  pick_rate: { label: "選取率", dir: "desc" },
  games: { label: "場數", dir: "desc" },
  gold: { label: "金幣", dir: "asc" },
};

export type ItemMetaMap = Record<number, ItemMeta>;

export function ItemTable({
  rows,
  meta,
  totalChampionGames,
  emptyMessage = "尚無裝備資料",
}: {
  rows: ItemStat[];
  meta: ItemMetaMap;
  totalChampionGames?: number | null;
  emptyMessage?: string;
}) {
  // null = use server order (already tier-then-winrate). Click a header to override.
  const [sortState, setSortState] = useState<{ col: SortKey; dir: "asc" | "desc" } | null>(null);

  const denom = totalChampionGames ?? null;
  const enriched = useMemo(
    () =>
      rows.map((r) => ({
        ...r,
        pick_rate: denom && denom > 0 ? r.games / denom : null,
      })),
    [rows, denom],
  );

  const sorted = useMemo(() => {
    if (!sortState) return enriched;
    const { col, dir } = sortState;
    const factor = dir === "asc" ? 1 : -1;
    return [...enriched].sort((a, b) => {
      let av: number | null;
      let bv: number | null;
      if (col === "gold") {
        av = meta[a.item_id]?.gold ?? null;
        bv = meta[b.item_id]?.gold ?? null;
      } else if (col === "pick_rate") {
        av = a.pick_rate;
        bv = b.pick_rate;
      } else {
        av = a[col];
        bv = b[col];
      }
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return ((av as number) - (bv as number)) * factor;
    });
  }, [enriched, meta, sortState]);

  const toggle = (k: SortKey) => {
    setSortState((cur) => {
      if (cur?.col === k) return { col: k, dir: cur.dir === "asc" ? "desc" : "asc" };
      return { col: k, dir: SORT_COLS[k].dir };
    });
  };
  const sort = sortState?.col ?? null;
  const dir = sortState?.dir ?? "desc";

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface px-4 py-10 text-center text-sm text-text-muted">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-surface-2 text-left text-[11px] uppercase tracking-wider text-text-dim">
            <th className="px-3 py-2.5 w-10">#</th>
            <th className="px-3 py-2.5 w-14">分級</th>
            <th className="px-3 py-2.5">裝備</th>
            <SortHeader col="gold" active={sort} dir={dir} onToggle={toggle} className="w-16 hidden md:table-cell" />
            <SortHeader col="win_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            {denom != null && (
              <SortHeader col="pick_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            )}
            <SortHeader col="games" active={sort} dir={dir} onToggle={toggle} className="w-16" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const m = meta[row.item_id];
            const iconUrl = cdragonAsset(m?.icon_path ?? null);
            const cleaned = cleanLolText(m?.description);
            const tip = cleaned ? (
              <span>
                <strong className="text-text">{m?.name}</strong>
                <span className="block text-text-muted">{truncate(cleaned, 220)}</span>
              </span>
            ) : null;
            return (
              <tr key={row.item_id} className="border-b border-border last:border-0 hover:bg-surface-2">
                <td className="px-3 py-2 text-text-dim tabular-nums">{i + 1}</td>
                <td className="px-3 py-2">
                  <TierBadge tier={row.tier} />
                </td>
                <td className="px-3 py-2">
                  <HoverTooltip content={tip}>
                    <span className="flex items-center gap-2.5">
                      {iconUrl ? (
                        <Image src={iconUrl} alt={m?.name ?? ""} width={28} height={28} className="rounded" unoptimized />
                      ) : (
                        <span className="inline-block h-7 w-7 rounded bg-surface-2" />
                      )}
                      <span className="font-medium">{m?.name ?? `Item #${row.item_id}`}</span>
                    </span>
                  </HoverTooltip>
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-text-dim hidden md:table-cell">
                  {m?.gold ?? "—"}
                </td>
                <td className="px-3 py-2 text-right font-medium tabular-nums">{formatPercent(row.win_rate)}</td>
                {denom != null && (
                  <td className="px-3 py-2 text-right tabular-nums text-text-muted">
                    {row.pick_rate != null ? formatPercent(row.pick_rate, 1) : "—"}
                  </td>
                )}
                <td className="px-3 py-2 text-right tabular-nums text-text-dim">{formatNumber(row.games)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SortHeader({
  col,
  active,
  dir,
  onToggle,
  className = "",
}: {
  col: SortKey;
  active: SortKey | null;
  dir: "asc" | "desc";
  onToggle: (k: SortKey) => void;
  className?: string;
}) {
  const isActive = active === col;
  const arrow = !isActive ? "" : dir === "asc" ? "▲" : "▼";
  return (
    <th className={`px-3 py-2.5 text-right ${className}`}>
      <button
        type="button"
        onClick={() => onToggle(col)}
        className={`-mx-1 inline-flex items-center gap-1 rounded px-1 py-0.5 transition hover:text-text ${
          isActive ? "text-accent-strong" : ""
        }`}
      >
        {SORT_COLS[col].label}
        <span className="text-[9px]">{arrow}</span>
      </button>
    </th>
  );
}
