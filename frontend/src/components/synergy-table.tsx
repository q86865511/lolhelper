"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { cdragonAsset } from "@/lib/cdragon";
import { formatNumber, formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";

export type SynergyRow = {
  partner_champion_id: number;
  games: number;
  wins: number;
  top1: number;
  win_rate: number;
  wilson_low: number;
  avg_placement: number | null;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

export type ChampionLite = { id: number; key: string; name: string; icon_path: string | null };

type SortKey = "win_rate" | "pick_rate" | "games";
const COLS: Record<SortKey, { label: string; dir: "asc" | "desc" }> = {
  win_rate: { label: "勝率", dir: "desc" },
  pick_rate: { label: "選取率", dir: "desc" },
  games: { label: "場數", dir: "desc" },
};

export function SynergyTable({
  rows,
  champions,
  totalChampionGames,
}: {
  rows: SynergyRow[];
  champions: Record<number, ChampionLite>;
  totalChampionGames?: number | null;
}) {
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
      const av = col === "pick_rate" ? a.pick_rate : a[col];
      const bv = col === "pick_rate" ? b.pick_rate : b[col];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return ((av as number) - (bv as number)) * factor;
    });
  }, [enriched, sortState]);

  const toggle = (k: SortKey) => {
    setSortState((cur) => {
      if (cur?.col === k) return { col: k, dir: cur.dir === "asc" ? "desc" : "asc" };
      return { col: k, dir: COLS[k].dir };
    });
  };
  const sort = sortState?.col ?? null;
  const dir = sortState?.dir ?? "desc";

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-surface px-4 py-8 text-center text-sm text-text-muted">
        尚無隊友資料(同隊樣本不足)。
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
            <th className="px-3 py-2.5">隊友英雄</th>
            <SortHead col="win_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            {denom != null && (
              <SortHead col="pick_rate" active={sort} dir={dir} onToggle={toggle} className="w-20" />
            )}
            <SortHead col="games" active={sort} dir={dir} onToggle={toggle} className="w-16" />
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => {
            const c = champions[r.partner_champion_id];
            const icon = cdragonAsset(c?.icon_path ?? null);
            return (
              <tr key={r.partner_champion_id} className="border-b border-border last:border-0 hover:bg-surface-2">
                <td className="px-3 py-2 text-text-dim tabular-nums">{i + 1}</td>
                <td className="px-3 py-2">
                  <TierBadge tier={r.tier} />
                </td>
                <td className="px-3 py-2">
                  {c ? (
                    <Link
                      href={`/arena/champions/${c.key}` as never}
                      className="flex items-center gap-2.5 hover:text-accent-strong"
                    >
                      {icon ? (
                        <Image src={icon} alt={c.name} width={28} height={28} className="rounded" unoptimized />
                      ) : (
                        <span className="inline-block h-7 w-7 rounded bg-surface-2" />
                      )}
                      <span className="font-medium">{c.name}</span>
                    </Link>
                  ) : (
                    <span className="text-text-dim">#{r.partner_champion_id}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right font-medium tabular-nums">{formatPercent(r.win_rate)}</td>
                {denom != null && (
                  <td className="px-3 py-2 text-right tabular-nums text-text-muted">
                    {r.pick_rate != null ? formatPercent(r.pick_rate, 1) : "—"}
                  </td>
                )}
                <td className="px-3 py-2 text-right tabular-nums text-text-dim">{formatNumber(r.games)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SortHead({
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
        {COLS[col].label}
        <span className="text-[9px]">{arrow}</span>
      </button>
    </th>
  );
}
