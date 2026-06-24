import { apiGet } from "@/lib/api-client";
import { formatNumber, formatRelativeTime } from "@/lib/format";
import { ArenaTabs } from "@/components/arena-tabs";
import { StatPill } from "@/components/stat-pill";
import { AugmentTable, type AugmentMetaMap } from "@/components/augment-table";

export const revalidate = 1800;

type AugmentStat = {
  augment_id: number;
  champion_id: number | null;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  avg_placement: number | null;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};
type Resp = {
  patch: string | null;
  patches_used: string[];
  queue_ids: number[];
  sample_size: number;
  updated_at: string | null;
  augments: AugmentStat[];
};
type AugmentMeta = {
  id: number;
  name: string;
  rarity: number | null;
  description: string | null;
  icon_path: string | null;
};

async function loadData() {
  try {
    const [stats, meta] = await Promise.all([
      apiGet<Resp>("/stats/arena/augments?with_rarity=true&min_games=30&limit=200"),
      apiGet<{ augments: AugmentMeta[] }>("/meta/augments"),
    ]);
    const metaMap: AugmentMetaMap = {};
    for (const a of meta.augments) metaMap[a.id] = a;
    return { stats, meta: metaMap, error: null as string | null };
  } catch (e) {
    return {
      stats: null,
      meta: {} as AugmentMetaMap,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

export default async function ArenaHex() {
  const { stats, meta, error } = await loadData();

  return (
    <main className="container mx-auto max-w-6xl px-4 py-8">
      <header className="mb-4">
        <div className="text-xs text-text-dim">競技場 · 海克斯 Augment</div>
        <h1 className="mt-1 text-2xl font-bold tracking-tight">海克斯 Augment 排行</h1>
        <p className="mt-1 text-sm text-text-muted">
          一場對戰開始時的固定 augment 選擇(銀 / 金 / 稜鏡稀有度)。滑鼠移到 augment 看詳細效果,點欄位標題排序。
        </p>
      </header>

      <ArenaTabs active="hex" />

      <section className="mt-5 flex flex-wrap items-center gap-2">
        <StatPill label="Patch" value={stats?.patches_used?.join(" + ") || "全部"} emphasize />
        <StatPill label="樣本" value={formatNumber(stats?.sample_size ?? 0)} />
        <StatPill label="更新" value={formatRelativeTime(stats?.updated_at ?? null)} />
        <StatPill label="最少場數" value="30" />
      </section>

      {error && (
        <div className="mt-6 rounded-md border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          無法載入:{error}
        </div>
      )}

      {stats && (
        <div className="mt-5">
          <AugmentTable
            rows={stats.augments}
            meta={meta}
            emptyMessage="還沒有達到 30 場樣本的海克斯 augment。再多跑幾輪 crawl 累積。"
          />
        </div>
      )}

      <p className="mt-4 text-xs text-text-dim">
        「Top4 勝率」= placement ≤ 4(進入第二輪)的比例。「Wilson」是 95% 信心下界,排序預設用。
      </p>
    </main>
  );
}
