import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { apiGet } from "@/lib/api-client";
import { cdragonAsset } from "@/lib/cdragon";
import { classifyItem } from "@/lib/item-category";
import { tierOrder } from "@/lib/tier-order";
import { formatNumber, formatPercent } from "@/lib/format";
import { ArenaTabs } from "@/components/arena-tabs";
import { type AugmentMetaMap } from "@/components/augment-table";
import { ItemTable, type ItemMetaMap } from "@/components/item-table";
import { ExpandableItemTable } from "@/components/expandable-item-table";
import {
  ChampionSidebar,
  type SidebarChampion,
} from "@/components/champion-sidebar";
import { SynergyTable, type ChampionLite } from "@/components/synergy-table";
import { RaritySelector } from "@/components/rarity-selector";
import { BuildPathsTable, type BuildPathRow } from "@/components/build-paths-table";

export const revalidate = 1800;

type ChampionMeta = {
  id: number;
  key: string;
  name: string;
  title: string | null;
  tags: string[] | null;
  icon_path: string | null;
};

type AugmentMeta = {
  id: number;
  name: string;
  rarity: number | null;
  description: string | null;
  icon_path: string | null;
};

type ItemMeta = {
  id: number;
  name: string;
  description: string | null;
  gold: number | null;
  tags: string[] | null;
  icon_path: string | null;
};

type OverallSummary = {
  games: number;
  wins: number;
  top1: number;
  win_rate: number;
  wilson_low: number;
  avg_placement: number | null;
} | null;

type AugmentStat = {
  augment_id: number;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type ItemStat = {
  item_id: number;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type SynergyRow = {
  partner_champion_id: number;
  games: number;
  wins: number;
  top1: number;
  win_rate: number;
  wilson_low: number;
  avg_placement: number | null;
  tier: "S" | "A" | "B" | "C" | "D" | null;
};

type ChampStatsResp = {
  champion_id: number;
  patch: string | null;
  patches_used: string[];
  overall: OverallSummary;
  top_augments: AugmentStat[];
  top_items: ItemStat[];
  synergies: SynergyRow[];
  build_paths: BuildPathRow[];
};

type ChampListResp = {
  patches_used: string[];
  champions: Array<{
    champion_id: number;
    games: number;
    win_rate: number;
    tier: "S" | "A" | "B" | "C" | "D" | null;
  }>;
};

async function loadData(champKey: string) {
  const champs = await apiGet<{ champions: ChampionMeta[] }>("/meta/champions");
  const champ = champs.champions.find(
    (c) => c.key.toLowerCase() === champKey.toLowerCase(),
  );
  if (!champ) return null;

  let stats: ChampStatsResp | null = null;
  let augMeta: AugmentMetaMap = {};
  let itemMeta: ItemMetaMap = {};
  let listStats: ChampListResp = { patches_used: [], champions: [] };
  try {
    const [s, augs, items, list] = await Promise.all([
      apiGet<ChampStatsResp>(
        `/stats/arena/champions/${champ.id}?with_rarity=true&top=50`,
      ),
      apiGet<{ augments: AugmentMeta[] }>("/meta/augments"),
      apiGet<{ items: ItemMeta[] }>("/meta/items").catch(() => ({
        items: [] as ItemMeta[],
      })),
      apiGet<ChampListResp>("/stats/arena/champions?min_games=5").catch(() => ({
        patches_used: [],
        champions: [],
      })),
    ]);
    stats = s;
    augMeta = {};
    for (const a of augs.augments) augMeta[a.id] = a;
    itemMeta = {};
    for (const i of items.items) itemMeta[i.id] = i;
    listStats = list;
  } catch {
    // Continue rendering with what we have
  }

  const listById = new Map(listStats.champions.map((s) => [s.champion_id, s]));
  const sidebar: SidebarChampion[] = champs.champions
    .map((c) => {
      const s = listById.get(c.id);
      return {
        id: c.id,
        key: c.key,
        name: c.name,
        icon_path: c.icon_path,
        win_rate: s ? s.win_rate : null,
        games: s ? s.games : 0,
        tier: s ? s.tier : null,
      };
    })
    .sort((a, b) => {
      // Tier-first ordering: all S together → A → B → C → D → no-tier.
      // Within the same tier, sort by win_rate desc.
      const ta = tierOrder(a.tier);
      const tb = tierOrder(b.tier);
      if (ta !== tb) return tb - ta;
      const wa = a.win_rate ?? -Infinity;
      const wb = b.win_rate ?? -Infinity;
      if (wa !== wb) return wb - wa;
      return a.name.localeCompare(b.name);
    });

  const partnerLite: Record<number, ChampionLite> = {};
  for (const c of champs.champions) {
    partnerLite[c.id] = { id: c.id, key: c.key, name: c.name, icon_path: c.icon_path };
  }

  return { champ, stats, augMeta, itemMeta, sidebar, partnerLite };
}

export default async function ChampionDetail({
  params,
}: {
  params: Promise<{ champKey: string }>;
}) {
  const { champKey } = await params;
  const data = await loadData(champKey);
  if (!data) notFound();
  const { champ, stats, augMeta, itemMeta, sidebar, partnerLite } = data;

  const portrait = cdragonAsset(champ.icon_path);
  const overall = stats?.overall ?? null;
  const totalGames = overall?.games ?? null;

  // Categorise items (prismatic detector now covers 443xxx/447xxx prismatic ranges)
  const bootsItems: ItemStat[] = [];
  const prismaticItems: ItemStat[] = [];
  const coreItems: ItemStat[] = [];
  for (const it of stats?.top_items ?? []) {
    const meta = itemMeta[it.item_id];
    const cat = classifyItem(meta);
    if (cat === "boots") bootsItems.push(it);
    else if (cat === "prismatic") prismaticItems.push(it);
    else if (cat === "core") coreItems.push(it);
  }

  return (
    <main className="container mx-auto max-w-7xl px-4 py-6">
      <nav className="mb-4 text-xs text-text-dim">
        <Link href="/arena" className="hover:text-text">競技場</Link>
        <span className="mx-1.5">/</span>
        <Link href="/arena/champions" className="hover:text-text">英雄</Link>
        <span className="mx-1.5">/</span>
        <span>{champ.name}</span>
      </nav>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
        <ChampionSidebar champions={sidebar} selectedKey={champ.key} />

        <div>
          <header className="mb-5 flex items-start gap-5">
            {portrait ? (
              <Image
                src={portrait}
                alt={champ.name}
                width={88}
                height={88}
                className="rounded-lg border border-border"
                unoptimized
              />
            ) : (
              <div className="h-22 w-22 rounded-lg bg-surface" />
            )}
            <div className="flex-1">
              <div className="text-xs text-text-dim">{champ.key}</div>
              <h1 className="text-3xl font-bold tracking-tight">{champ.name}</h1>
              {champ.title && <div className="mt-1 text-sm text-text-muted">{champ.title}</div>}
              {champ.tags && champ.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {champ.tags.map((t) => (
                    <span key={t} className="rounded border border-border bg-surface px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-text-muted">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </header>

          <ArenaTabs active="champions" />

          {stats && (
            <section className="mt-5 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-md border border-border bg-surface px-3 py-1.5">
                <span className="text-text-dim">Patch </span>
                <strong className="text-text">
                  {stats.patches_used.join(" + ") || "全部"}
                </strong>
              </span>
            </section>
          )}

          {overall && (
            <section className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
              <StatBox label="樣本場數" value={formatNumber(overall.games)} />
              <StatBox label="勝率" value={formatPercent(overall.win_rate)} emphasize />
              <StatBox
                label="平均名次"
                value={overall.avg_placement?.toFixed(2) ?? "—"}
              />
            </section>
          )}

          {!stats ? (
            <div className="mt-6 rounded-md border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
              這個英雄的對戰樣本還不足以產生統計。讓 ARQ worker 多跑一陣子。
            </div>
          ) : (
            <>
              <section className="mt-7">
                <SectionHeader title="海克斯 Augment" hint="點分類切換稀有度。滑鼠移上看效果。" />
                <div className="mt-3">
                  <RaritySelector
                    augments={stats.top_augments}
                    meta={augMeta}
                    totalChampionGames={totalGames}
                  />
                </div>
              </section>

              <section className="mt-8">
                <SectionHeader title="該英雄裝備" hint="鞋子 / 稜鏡(預設 5 件)/ 核心裝備分組。" />
                <div className="mt-3 space-y-5">
                  <CategorySection title="鞋子" subtitle="移動鞋類選項勝率">
                    <ItemTable
                      rows={bootsItems}
                      meta={itemMeta}
                      totalChampionGames={totalGames}
                      emptyMessage="尚無鞋子資料(樣本不足)"
                    />
                  </CategorySection>
                  <CategorySection
                    title="稜鏡裝備"
                    subtitle="由「稜鏡能力值鐵砧」augment 或事件抽到的選項"
                  >
                    <ExpandableItemTable
                      rows={prismaticItems}
                      meta={itemMeta}
                      defaultShow={5}
                      totalChampionGames={totalGames}
                      emptyMessage="尚無稜鏡裝備樣本(該英雄稀有)"
                    />
                  </CategorySection>
                  <CategorySection title="核心裝備" subtitle="完整裝備(1000 金以上)">
                    <ItemTable
                      rows={coreItems}
                      meta={itemMeta}
                      totalChampionGames={totalGames}
                      emptyMessage="尚無核心裝備樣本"
                    />
                  </CategorySection>
                </div>
              </section>

              <section className="mt-8">
                <SectionHeader
                  title="核心組建"
                  hint="2-3 件核心裝備的最熱門組合(已排除小身、鞋子、稜鏡)。"
                />
                <div className="mt-3">
                  <BuildPathsTable rows={stats.build_paths} meta={itemMeta} />
                </div>
              </section>

              <section className="mt-8">
                <SectionHeader
                  title="英雄搭配"
                  hint="此英雄與該隊友同隊時的勝率。"
                />
                <div className="mt-3">
                  <SynergyTable
                    rows={stats.synergies}
                    champions={partnerLite}
                    totalChampionGames={totalGames}
                  />
                </div>
              </section>

              <section className="mt-8 rounded-lg border border-border bg-surface p-4 text-sm text-text-muted">
                <div className="font-semibold text-text">技能順序與點法</div>
                <p className="mt-1 text-xs">
                  需要 Riot Match-V5 timeline API 抓 SKILL_LEVEL_UP 事件才能計算 — 列在下一階段
                  (請見之前回覆中的「路線圖」)。
                </p>
              </section>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

function StatBox({ label, value, emphasize }: { label: string; value: string; emphasize?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2.5">
      <div className="text-[11px] text-text-dim">{label}</div>
      <div className={`mt-1 tabular-nums ${emphasize ? "text-xl font-bold text-accent-strong" : "text-lg font-semibold"}`}>
        {value}
      </div>
    </div>
  );
}

function SectionHeader({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between">
      <h2 className="text-lg font-semibold">{title}</h2>
      {hint && <span className="text-xs text-text-dim">{hint}</span>}
    </div>
  );
}

function CategorySection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        {subtitle && <span className="text-[11px] text-text-dim">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}
