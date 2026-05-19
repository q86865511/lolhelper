/** API response envelope conventions, kept in sync with backend Pydantic schemas. */

export type Tier = "S" | "A" | "B" | "C" | "D";

export type Patch = string; // e.g. "15.10"

export type QueueId = 1700 | 1710 | 2400 | number;

export interface SourceBreakdown {
  riot_api: number;
  lcu_upload: number;
}

export interface ArenaAugmentStat {
  augment_id: number;
  champion_id: number | null;
  games: number;
  wins: number;
  win_rate: number;
  wilson_low: number;
  avg_placement: number | null;
  tier: Tier | null;
}

export interface ArenaAugmentsResponse {
  patch: Patch | null;
  queue_ids: QueueId[];
  sample_size: number;
  updated_at: string | null;
  augments: ArenaAugmentStat[];
}

export interface ArenaChampionDetail {
  champion_id: number;
  patch: Patch | null;
  top_augments: Array<{
    augment_id: number;
    games: number;
    win_rate: number;
    wilson_low: number;
    tier: Tier | null;
  }>;
  top_items: Array<{
    item_id: number;
    games: number;
    win_rate: number;
    wilson_low: number;
    tier: Tier | null;
  }>;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  env: string;
  db: "ok" | "down";
  redis: "ok" | "down";
  riot_keys_loaded: number;
}
