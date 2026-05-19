"use client";

import Image from "next/image";
import { useMemo, useState } from "react";
import { cdragonAsset } from "@/lib/cdragon";
import { cleanLolText, truncate } from "@/lib/lol-text";
import { formatNumber, formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";
import { HoverTooltip } from "@/components/hover-tooltip";
import type { ItemMetaMap } from "@/components/item-table";

export type BuildPathRow = {
  items: number[];
  games: number;
  wins: number;
  top1: number;
  win_rate: number;
  top1_rate: number;
  wilson_low: number;
  pick_rate: number | null;
  avg_placement: number | null;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type SortKey = "win_rate" | "top1_rate" | "pick_rate" | "games" | "avg_placement";

const SORT_COLS: Record<SortKey, { label: string; dir: "asc" | "desc" }> = {
  win_rate: { label: "勝率", dir: "desc" },
  top1_rate: { label: "第一名率", dir: "desc" },
  pick_rate: { label: "選用率", dir: "desc" },
  games: { label: "場數", dir: "desc" },
  avg_placement: { label: "平均名次", dir: "asc" },
};

export function BuildPathsTable({
  rows,
  meta,
  emptyMessage = "尚無核心組建資料",
}: {
  rows: BuildPathRow[];
  meta: ItemMetaMap;
  emptyMessage?: string;
}) {
  const [sortState, setSortState] = useState<
    { col: SortKey; dir: "asc" | "desc" } | null
  >(null);

  const sorted = useMemo(() => {
    if (!sortState) return rows;
    const { col, dir } = sortState;
    const factor = dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const av = a[col];
      const bv = b[col];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return ((av as number) - (bv as number)) * factor;
    });
  }, [rows, sortState]);

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
      <div className="rounded-lg border border-border bg-surface px-4 py-8 text-center text-sm text-text-muted">
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
            <th className="px-3 py-2.5">核心組建</th>
            <SortHeader col="avg_placement" active={sort} dir={dir} onToggle={toggle} className="w-20 hidden md:table-cell" />
            <SortHeader col="top1_rate" active={sort} dir={dir} onToggle={toggle} className="w-24 hidden lg:table-cell" />
            <SortHeader col="pick_rate" active={sort} dir={dir} onToggle={toggle} className="w-24" />
            <SortHeader col="win_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            <SortHeader col="games" active={sort} dir={dir} onToggle={toggle} className="w-16 hidden sm:table-cell" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.items.join("-")} className="border-b border-border last:border-0 hover:bg-surface-2">
              <td className="px-3 py-2 text-text-dim tabular-nums">{i + 1}</td>
              <td className="px-3 py-2">
                <TierBadge tier={row.tier} />
              </td>
              <td className="px-3 py-2">
                <BuildChain items={row.items} meta={meta} />
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-text-muted hidden md:table-cell">
                {row.avg_placement?.toFixed(2) ?? "—"}
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-text-muted hidden lg:table-cell">
                {formatPercent(row.top1_rate, 1)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-text-muted">
                <div className="leading-tight">
                  <div className="font-medium text-text">
                    {row.pick_rate != null ? formatPercent(row.pick_rate, 2) : "—"}
                  </div>
                  <div className="text-[10px] text-text-dim">{formatNumber(row.games)} 場</div>
                </div>
              </td>
              <td className="px-3 py-2 text-right font-medium tabular-nums text-accent-strong">
                {formatPercent(row.win_rate)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-text-dim hidden sm:table-cell">
                {formatNumber(row.games)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BuildChain({ items, meta }: { items: number[]; meta: ItemMetaMap }) {
  return (
    <div className="flex items-center gap-1">
      {items.map((id, idx) => {
        const m = meta[id];
        const url = cdragonAsset(m?.icon_path ?? null);
        const cleaned = cleanLolText(m?.description);
        const tip = cleaned ? (
          <span>
            <strong className="text-text">{m?.name}</strong>
            <span className="block text-text-muted">{truncate(cleaned, 220)}</span>
          </span>
        ) : (
          <strong className="text-text">{m?.name ?? `#${id}`}</strong>
        );
        return (
          <span key={`${id}-${idx}`} className="inline-flex items-center gap-1">
            <HoverTooltip content={tip}>
              {url ? (
                <Image src={url} alt={m?.name ?? ""} width={32} height={32} className="rounded border border-border" unoptimized />
              ) : (
                <span className="inline-block h-8 w-8 rounded border border-border bg-surface-2" />
              )}
            </HoverTooltip>
            {idx < items.length - 1 && (
              <span className="text-text-dim text-sm">▸</span>
            )}
          </span>
        );
      })}
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
