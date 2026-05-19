/** Tier sort priority — higher number = better tier. Used as the primary sort
 * key so leaderboards group all S together, then A, B, C, D. */

export type Tier = "S" | "A" | "B" | "C" | "D" | null | undefined;

const ORDER: Record<string, number> = {
  S: 5,
  A: 4,
  B: 3,
  C: 2,
  D: 1,
};

/** Returns the priority used by sort comparators. Null/undefined => 0 (last). */
export function tierOrder(tier: Tier): number {
  if (!tier) return 0;
  return ORDER[tier] ?? 0;
}

/** Generic comparator: sort by tier desc, then by `winRate` desc. */
export function compareByTierThenWinRate<
  T extends { tier?: Tier; win_rate?: number | null },
>(a: T, b: T): number {
  const ta = tierOrder(a.tier);
  const tb = tierOrder(b.tier);
  if (ta !== tb) return tb - ta;
  const wa = a.win_rate ?? -Infinity;
  const wb = b.win_rate ?? -Infinity;
  return wb - wa;
}
