import { redirect } from "next/navigation";
import { apiGet } from "@/lib/api-client";

/**
 * Champion entry point: pick the top-Wilson champion and redirect to its detail page.
 * The detail page sidebar lets the user browse all champions from there.
 */

type ChampionMeta = { id: number; key: string };

type ChampionsListResp = {
  champions: Array<{
    champion_id: number;
    games: number;
    wilson_low: number;
    tier: string | null;
  }>;
};

export default async function ArenaChampionsRedirect() {
  let key = "Yasuo"; // fallback if API unreachable

  try {
    const [list, meta] = await Promise.all([
      apiGet<ChampionsListResp>("/stats/arena/champions?min_games=5"),
      apiGet<{ champions: ChampionMeta[] }>("/meta/champions"),
    ]);
    if (list.champions.length > 0) {
      const top = list.champions[0];
      const m = meta.champions.find((c) => c.id === top.champion_id);
      if (m) key = m.key;
    }
  } catch {
    // keep fallback
  }

  redirect(`/arena/champions/${key}`);
}
