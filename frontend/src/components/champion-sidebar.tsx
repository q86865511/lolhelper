"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import { cdragonAsset } from "@/lib/cdragon";
import { formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";

export type SidebarChampion = {
  id: number;
  key: string;
  name: string;
  icon_path: string | null;
  win_rate: number | null;
  games: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

export function ChampionSidebar({
  champions,
  selectedKey,
}: {
  champions: SidebarChampion[];
  selectedKey: string;
}) {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => {
    if (!q.trim()) return champions;
    const needle = q.trim().toLowerCase();
    return champions.filter(
      (c) =>
        c.name.toLowerCase().includes(needle) ||
        c.key.toLowerCase().includes(needle),
    );
  }, [champions, q]);

  return (
    <aside className="hidden lg:block">
      <div className="sticky top-16 rounded-lg border border-border bg-surface">
        <div className="border-b border-border p-3">
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜尋英雄"
            className="w-full rounded-md border border-border bg-bg px-3 py-1.5 text-sm outline-none placeholder:text-text-dim focus:border-accent-strong"
          />
          <div className="mt-2 text-[11px] text-text-dim">
            {filtered.length} / {champions.length} 英雄
          </div>
        </div>
        <div className="max-h-[calc(100vh-220px)] overflow-y-auto">
          <ul>
            {filtered.map((c) => {
              const icon = cdragonAsset(c.icon_path);
              const active = c.key.toLowerCase() === selectedKey.toLowerCase();
              return (
                <li key={c.id}>
                  <Link
                    href={`/arena/champions/${c.key}` as never}
                    className={`flex items-center gap-2 border-l-2 px-2.5 py-1.5 transition ${
                      active
                        ? "border-l-accent-strong bg-surface-2 text-text"
                        : "border-l-transparent text-text-muted hover:bg-surface-2 hover:text-text"
                    }`}
                  >
                    {icon ? (
                      <Image src={icon} alt={c.name} width={26} height={26} className="rounded" unoptimized />
                    ) : (
                      <span className="inline-block h-6 w-6 rounded bg-bg" />
                    )}
                    <span className="min-w-0 flex-1 truncate text-sm">{c.name}</span>
                    {c.tier ? (
                      <TierBadge tier={c.tier} size="sm" />
                    ) : (
                      <span className="text-[10px] text-text-dim">—</span>
                    )}
                    {c.win_rate != null && (
                      <span className="w-12 text-right text-[11px] tabular-nums text-text-dim">
                        {formatPercent(c.win_rate, 0)}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </aside>
  );
}
