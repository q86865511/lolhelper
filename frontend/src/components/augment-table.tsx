"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { cdragonAsset } from "@/lib/cdragon";
import { cleanLolText, truncate } from "@/lib/lol-text";
import { formatNumber, formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";
import { HoverTooltip } from "@/components/hover-tooltip";

type AugmentStat = {
  augment_id: number;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type AugmentMeta = {
  id: number;
  name: string;
  rarity: number | null;
  icon_path: string | null;
  description?: string | null;
};

type SortKey = "win_rate" | "pick_rate" | "games";

const SORT_COLS: Record<SortKey, { label: string; dir: "asc" | "desc" }> = {
  win_rate: { label: "勝率", dir: "desc" },
  pick_rate: { label: "選取率", dir: "desc" },
  games: { label: "場數", dir: "desc" },
};

type SortState = { col: SortKey; dir: "asc" | "desc" } | null;

export type AugmentMetaMap = Record<number, AugmentMeta>;

export function AugmentTable({
  rows,
  meta,
  totalChampionGames,
  emptyMessage = "尚無資料",
}: {
  rows: AugmentStat[];
  meta: AugmentMetaMap;
  totalChampionGames?: number | null;
  emptyMessage?: string;
}) {
  // null = use server order (already sorted by tier-then-winrate). Clicking a
  // header switches to that column's sort.
  const [sortState, setSortState] = useState<SortState>(null);

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
      const av = col === "pick_rate" ? a.pick_rate : a[col];
      const bv = col === "pick_rate" ? b.pick_rate : b[col];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return ((av as number) - (bv as number)) * factor;
    });
  }, [enriched, sortState]);

  const toggle = (key: SortKey) => {
    setSortState((cur) => {
      if (cur?.col === key) return { col: key, dir: cur.dir === "asc" ? "desc" : "asc" };
      return { col: key, dir: SORT_COLS[key].dir };
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
            <th className="px-3 py-2.5">Augment</th>
            <SortHeader col="win_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            {denom != null && (
              <SortHeader col="pick_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            )}
            <SortHeader col="games" active={sort} dir={dir} onToggle={toggle} className="w-16" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const m = meta[row.augment_id];
            const iconUrl = cdragonAsset(m?.icon_path ?? null);
            const cleaned = cleanLolText(m?.description);
            const tooltipContent = cleaned ? (
              <span>
                <strong className="text-text">{m?.name}</strong>
                <span className="block text-text-muted">{truncate(cleaned, 220)}</span>
              </span>
            ) : null;
            return (
              <tr key={row.augment_id} className="border-b border-border last:border-0 hover:bg-surface-2">
                <td className="px-3 py-2 text-text-dim tabular-nums">{i + 1}</td>
                <td className="px-3 py-2">
                  <TierBadge tier={row.tier} />
                </td>
                <td className="px-3 py-2">
                  <HoverTooltip content={tooltipContent}>
                    <span className="flex items-center gap-2.5">
                      {iconUrl ? (
                        <Image src={iconUrl} alt={m?.name ?? ""} width={28} height={28} className="rounded" unoptimized />
                      ) : (
                        <span className="inline-block h-7 w-7 rounded bg-surface-2" />
                      )}
                      <span className="font-medium text-text">{m?.name ?? `Augment #${row.augment_id}`}</span>
                    </span>
                  </HoverTooltip>
                </td>
                <td className="px-3 py-2 text-right font-medium tabular-nums">
                  {formatPercent(row.win_rate)}
                </td>
                {denom != null && (
                  <td className="px-3 py-2 text-right tabular-nums text-text-muted">
                    {row.pick_rate != null ? formatPercent(row.pick_rate, 1) : "—"}
                  </td>
                )}
                <td className="px-3 py-2 text-right tabular-nums text-text-dim">
                  {formatNumber(row.games)}
                </td>
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
