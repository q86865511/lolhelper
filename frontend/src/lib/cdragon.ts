/**
 * Community Dragon asset URL helpers.
 *
 * Community Dragon stores all asset paths as `/lol-game-data/...` but serves
 * them at the lowercase URL under `plugins/rcp-be-lol-game-data/global/default`.
 */

const CDRAGON_BASE =
  "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default";

export function cdragonAsset(path: string | null | undefined): string | null {
  if (!path) return null;
  let p = path.toLowerCase();
  // CDragon strips the "/lol-game-data/assets" prefix in its served paths
  p = p.replace(/^\/lol-game-data\/assets/, "");
  if (!p.startsWith("/")) p = `/${p}`;
  return `${CDRAGON_BASE}${p}`;
}
