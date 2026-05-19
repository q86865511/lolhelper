import { apiGet } from "@/lib/api-client";
import { formatNumber } from "@/lib/format";
import { ArenaTabs } from "@/components/arena-tabs";
import { StatPill } from "@/components/stat-pill";
import { ItemsCategoryPage } from "@/components/items-category-page";
import type { ItemMetaMap } from "@/components/item-table";

export const revalidate = 1800;

type ItemStat = {
  item_id: number;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type ItemsResp = {
  patch: string | null;
  patches_used: string[];
  category: string | null;
  total_player_games: number;
  items: ItemStat[];
};

type ItemMeta = {
  id: number;
  name: string;
  description: string | null;
  gold: number | null;
  tags: string[] | null;
  icon_path: string | null;
};

async function loadData() {
  try {
    const [core, prismatic, boots, items] = await Promise.all([
      apiGet<ItemsResp>("/stats/arena/items?category=core&min_games=30&limit=300"),
      apiGet<ItemsResp>("/stats/arena/items?category=prismatic&min_games=10&limit=200"),
      apiGet<ItemsResp>("/stats/arena/items?category=boots&min_games=30&limit=100"),
      apiGet<{ items: ItemMeta[] }>("/meta/items"),
    ]);
    const meta: ItemMetaMap = {};
    for (const i of items.items) meta[i.id] = i;
    return {
      meta,
      buckets: [
        { category: "core" as const, items: core.items, totalPlayerGames: core.total_player_games },
        { category: "prismatic" as const, items: prismatic.items, totalPlayerGames: prismatic.total_player_games },
        { category: "boots" as const, items: boots.items, totalPlayerGames: boots.total_player_games },
      ],
      patchesUsed: core.patches_used,
      totalGames: core.total_player_games,
      error: null as string | null,
    };
  } catch (e) {
    return {
      meta: {} as ItemMetaMap,
      buckets: [],
      patchesUsed: [] as string[],
      totalGames: 0,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

export default async function ArenaItems() {
  const { meta, buckets, patchesUsed, totalGames, error } = await loadData();

  return (
    <main className="container mx-auto max-w-6xl px-4 py-8">
      <header className="mb-4">
        <div className="text-xs text-text-dim">競技場 · 裝備</div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">裝備排行</h1>
        <p className="mt-1 text-sm text-text-muted">
          全英雄跨對戰聚合的裝備統計。分核心 / 稜鏡 / 鞋子三類,點分頁切換。
        </p>
      </header>

      <ArenaTabs active="items" />

      <section className="mt-5 flex flex-wrap items-center gap-2">
        <StatPill label="Patch" value={patchesUsed.join(" + ") || "全部"} emphasize />
        <StatPill label="樣本玩家數" value={formatNumber(totalGames)} />
      </section>

      {error && (
        <div className="mt-6 rounded-md border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          無法載入:{error}
        </div>
      )}

      {buckets.length > 0 && <ItemsCategoryPage buckets={buckets} meta={meta} />}
    </main>
  );
}
