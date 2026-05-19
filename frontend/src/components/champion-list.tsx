"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { cdragonAsset } from "@/lib/cdragon";
import { formatNumber, formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";

export type ChampionRow = {
  champion_id: number;
  key: string;
  name: string;
  icon_path: string | null;
  games: number;
  wins: number;
  top1: number;
  win_rate: number;
  wilson_low: number;
  avg_placement: number | null;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type SortKey = "wilson_low" | "win_rate" | "avg_placement" | "top1" | "games";

const SORT_COLS: Record<SortKey, { label: string; dir: "asc" | "desc" }> = {
  wilson_low: { label: "Wilson", dir: "desc" },
  win_rate: { label: "Top4 勝率", dir: "desc" },
  avg_placement: { label: "平均名次", dir: "asc" },
  top1: { label: "第一名次數", dir: "desc" },
  games: { label: "場數", dir: "desc" },
};

export function ChampionList({ rows }: { rows: ChampionRow[] }) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortKey>("wilson_low");
  const [dir, setDir] = useState<"asc" | "desc">("desc");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const base = !needle
      ? rows
      : rows.filter(
          (c) =>
            c.name.toLowerCase().includes(needle) ||
            c.key.toLowerCase().includes(needle),
        );
    const factor = dir === "asc" ? 1 : -1;
    return [...base].sort((a, b) => {
      const av = a[sort];
      const bv = b[sort];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return ((av as number) - (bv as number)) * factor;
    });
  }, [rows, q, sort, dir]);

  const toggle = (k: SortKey) => {
    if (sort === k) setDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSort(k);
      setDir(SORT_COLS[k].dir);
    }
  };

  return (
    <>
      <div className="mt-5">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜尋英雄(中文或英文 key)…"
          className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm outline-none placeholder:text-text-dim focus:border-accent-strong"
        />
      </div>
      <div className="mt-2 text-xs text-text-dim">
        共 {filtered.length} / {rows.length} 英雄
      </div>
      <div className="mt-3 overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2 text-left text-[11px] uppercase tracking-wider text-text-dim">
              <th className="px-3 py-2.5 w-10">#</th>
              <th className="px-3 py-2.5 w-14">Tier</th>
              <th className="px-3 py-2.5">英雄</th>
              <SortHeader col="win_rate" active={sort} dir={dir} onToggle={toggle} className="w-24" />
              <SortHeader col="avg_placement" active={sort} dir={dir} onToggle={toggle} className="w-24 hidden md:table-cell" />
              <SortHeader col="top1" active={sort} dir={dir} onToggle={toggle} className="w-24 hidden lg:table-cell" />
              <SortHeader col="wilson_low" active={sort} dir={dir} onToggle={toggle} className="w-20" />
              <SortHeader col="games" active={sort} dir={dir} onToggle={toggle} className="w-16" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((c, i) => {
              const icon = cdragonAsset(c.icon_path);
              const top1Rate = c.games > 0 ? c.top1 / c.games : 0;
              return (
                <tr key={c.champion_id} className="border-b border-border last:border-0 hover:bg-surface-2">
                  <td className="px-3 py-2 text-text-dim tabular-nums">{i + 1}</td>
                  <td className="px-3 py-2">
                    <TierBadge tier={c.tier} />
                  </td>
                  <td className="px-3 py-2">
                    <Link
                      href={`/arena/champions/${c.key}` as never}
                      className="flex items-center gap-2.5 hover:text-accent-strong"
                    >
                      {icon ? (
                        <Image src={icon} alt={c.name} width={28} height={28} className="rounded" unoptimized />
                      ) : (
                        <span className="inline-block h-7 w-7 rounded bg-surface-2" />
                      )}
                      <span className="leading-tight">
                        <span className="block font-medium">{c.name}</span>
                        <span className="block text-[11px] text-text-dim">{c.key}</span>
                      </span>
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-right font-medium tabular-nums">
                    {formatPercent(c.win_rate)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-muted hidden md:table-cell">
                    {c.avg_placement?.toFixed(2) ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-muted hidden lg:table-cell">
                    {formatPercent(top1Rate, 1)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-muted">
                    {formatPercent(c.wilson_low, 1)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-text-dim">
                    {formatNumber(c.games)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="px-4 py-8 text-center text-sm text-text-muted">沒有符合的英雄。</div>
        )}
      </div>
    </>
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
  active: SortKey;
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
