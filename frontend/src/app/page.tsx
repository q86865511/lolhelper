import Link from "next/link";
import Image from "next/image";
import { apiGet } from "@/lib/api-client";
import { cdragonAsset } from "@/lib/cdragon";
import { formatNumber, formatPercent } from "@/lib/format";
import { TierBadge } from "@/components/tier-badge";

export const revalidate = 1800;

type AugmentStat = {
  augment_id: number;
  games: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type AugmentsResp = { sample_size: number; augments: AugmentStat[] };
type MetaResp = { augments: Array<{ id: number; name: string; icon_path: string | null }> };

async function loadTop() {
  try {
    const [stats, meta] = await Promise.all([
      apiGet<AugmentsResp>("/stats/arena/augments?with_rarity=true&min_games=50&limit=5"),
      apiGet<MetaResp>("/meta/augments"),
    ]);
    const metaById = new Map(meta.augments.map((a) => [a.id, a]));
    return { topAugments: stats.augments, sample: stats.sample_size, metaById, error: null as string | null };
  } catch (e) {
    return {
      topAugments: [] as AugmentStat[],
      sample: 0,
      metaById: new Map<number, { id: number; name: string; icon_path: string | null }>(),
      error: e instanceof Error ? e.message : String(e),
    };
  }
}

export default async function HomePage() {
  const { topAugments, sample, metaById, error } = await loadTop();

  return (
    <main>
      <section className="border-b border-border bg-gradient-to-b from-surface to-bg">
        <div className="container mx-auto max-w-6xl px-4 py-16">
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
            LoL 競技場 &amp; 海克斯大亂鬥
            <br />
            <span className="text-accent-strong">augment 即時統計</span>
          </h1>
          <p className="mt-4 max-w-2xl text-text-muted">
            來自 Riot Match-V5 高分玩家的競技場對戰聚合,並用 Wilson 下界排序。
            海克斯大亂鬥透過 .exe 客戶端 crowdsource(M2 推出)。
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/arena"
              className="rounded-md bg-accent-strong px-5 py-2.5 text-sm font-semibold text-bg transition hover:bg-accent"
            >
              查看 Augment 排行 →
            </Link>
            <Link
              href="/arena/champions"
              className="rounded-md border border-border bg-surface px-5 py-2.5 text-sm transition hover:border-border-strong"
            >
              依英雄查看
            </Link>
            <Link
              href="/download"
              className="rounded-md border border-border bg-surface px-5 py-2.5 text-sm transition hover:border-border-strong"
            >
              下載 .exe(M2)
            </Link>
          </div>
        </div>
      </section>

      <section className="container mx-auto max-w-6xl px-4 py-12">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Link
            href="/arena"
            className="group rounded-lg border border-border bg-surface p-6 transition hover:border-border-strong hover:bg-surface-2"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-accent">queueId 1700 / 1710</div>
                <h2 className="mt-1 text-xl font-bold">競技場 Arena</h2>
              </div>
              <span className="text-text-dim transition group-hover:translate-x-1 group-hover:text-text">→</span>
            </div>
            <p className="mt-3 text-sm text-text-muted">
              8 隊 2v2 死鬥。Augment 三選一 + 裝備推薦。
            </p>
            <div className="mt-4 text-xs text-text-dim">
              ✓ Riot 官方 API 支援 ・ ✓ 高分群聚合
            </div>
          </Link>

          <Link
            href="/mayhem"
            className="group rounded-lg border border-border bg-surface p-6 transition hover:border-border-strong hover:bg-surface-2"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-amber-400">queueId 2400</div>
                <h2 className="mt-1 text-xl font-bold">海克斯大亂鬥 Mayhem</h2>
              </div>
              <span className="text-text-dim transition group-hover:translate-x-1 group-hover:text-text">→</span>
            </div>
            <p className="mt-3 text-sm text-text-muted">
              ARAM × Augments。Riot API 封鎖,資料靠 .exe crowdsource。
            </p>
            <div className="mt-4 text-xs text-amber-400/80">
              ⚠ 等候 .exe 客戶端累積資料(M2)
            </div>
          </Link>
        </div>
      </section>

      <section className="container mx-auto max-w-6xl px-4 pb-16">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-lg font-semibold">熱門海克斯 Augment (Top 5)</h2>
          <div className="text-xs text-text-dim">樣本 {formatNumber(sample)}</div>
        </div>
        <div className="mb-3 rounded-md border border-border bg-surface/50 p-3 text-xs text-text-muted">
          <strong className="text-text">資料來源</strong>:
          來自 Riot Match-V5 API,聚合 <strong>韓國 (KR) / 日本 (JP1) / 台灣 (TW2)</strong> 三個伺服器的
          <strong>挑戰者 + 大師</strong>牌位玩家(以高分玩家為起點 BFS 擴張)。
          <strong className="text-text"> 不是您個人的對戰</strong> — 是世界資料聚合。
          樣本越大,Wilson 下界越接近真實勝率;小樣本會被自動懲罰排序。
        </div>

        {error ? (
          <div className="rounded-md border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
            無法載入:{error}
            <div className="mt-2 text-red-200/80">
              請確認後端在執行:{" "}
              <code className="rounded bg-black/30 px-1 font-mono">uv run uvicorn app.main:app --reload</code>
            </div>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border">
            <div className="divide-y divide-border">
              {topAugments.map((row, i) => {
                const m = metaById.get(row.augment_id);
                const iconUrl = cdragonAsset(m?.icon_path ?? null);
                return (
                  <div
                    key={row.augment_id}
                    className="flex items-center gap-4 bg-surface px-4 py-3 hover:bg-surface-2"
                  >
                    <span className="w-6 text-sm text-text-dim">{i + 1}</span>
                    <TierBadge tier={row.tier} size="sm" />
                    {iconUrl ? (
                      <Image
                        src={iconUrl}
                        alt={m?.name ?? ""}
                        width={32}
                        height={32}
                        className="rounded"
                        unoptimized
                      />
                    ) : (
                      <div className="h-8 w-8 rounded bg-surface-2" />
                    )}
                    <span className="flex-1 font-medium">{m?.name ?? `#${row.augment_id}`}</span>
                    <span className="text-sm tabular-nums">{formatPercent(row.win_rate)}</span>
                    <span className="w-24 text-right text-sm text-text-muted tabular-nums">
                      {formatNumber(row.games)} 場
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
