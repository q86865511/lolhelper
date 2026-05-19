/** Categorise Arena items into boots / prismatic / core for grouped display.
 *
 * Arena uses several item-ID namespaces:
 *   - 220xxx: anvil tokens / consumables (skipped)
 *   - 221xxx–223xxx: components and legendary items (boots & core)
 *   - 226xxx: legendary upgrades (2500–2750 gold)
 *   - 228xxx: prismatic anvil drops (6000+ gold typical)
 *   - 443xxx / 444xxx / 446xxx / 447xxx: prismatic event-bought items (2750 gold)
 *   - 322xxx / 323xxx: stat-altered variants (treated as core)
 */

export type ItemCategory = "boots" | "prismatic" | "core" | "other";

export interface ItemMetaLite {
  id: number;
  gold: number | null;
  tags: string[] | null;
}

function isPrismatic(meta: ItemMetaLite): boolean {
  const id = meta.id;
  const gold = meta.gold ?? 0;
  // Anvil-given prismatic items
  if (id >= 228000 && id <= 228999 && gold >= 2750) return true;
  // Event-bought prismatic. Must be 2750+ — 2500 in this range is a legendary variant.
  if (id >= 443000 && id <= 447999 && gold >= 2750) return true;
  return false;
}

function isBoots(meta: ItemMetaLite): boolean {
  return Array.isArray(meta.tags) && meta.tags.includes("Boots");
}

export function classifyItem(meta: ItemMetaLite | undefined): ItemCategory {
  if (!meta) return "other";
  if (isPrismatic(meta)) return "prismatic";
  if (isBoots(meta)) return "boots";
  if ((meta.gold ?? 0) >= 1000) return "core";
  return "other";
}
