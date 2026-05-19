/**
 * Strip Riot/CDragon markup from descriptions so they read as plain text.
 *
 * Examples of what gets removed:
 *   <crit>暴擊</crit>          → 暴擊
 *   <br>                       → \n
 *   %i:StatAnvil%稜鏡          → 稜鏡
 *   @CritGranted@              → ?  (unresolved variable)
 *   @HealthPercentageMod*100@  → ?
 */
export function cleanLolText(html: string | null | undefined): string {
  if (!html) return "";
  let s = String(html);

  // Convert <br> tags (and variants) to newlines first
  s = s.replace(/<br\s*\/?>/gi, "\n");
  // Remove all other tags
  s = s.replace(/<[^>]+>/g, "");
  // Remove icon placeholders like %i:StatAnvil%
  s = s.replace(/%i:[^%]+%/g, "");
  // Replace unresolved variables (@something@ or @something*100@) with ?
  s = s.replace(/@[^@]+@/g, "?");
  // Collapse runs of whitespace, keep single newlines
  s = s.replace(/[ \t]+/g, " ").replace(/\n[ \t]+/g, "\n");
  return s.trim();
}

export function truncate(s: string, max = 160): string {
  if (s.length <= max) return s;
  return s.slice(0, max - 1).trimEnd() + "…";
}
