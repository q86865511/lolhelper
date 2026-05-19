export interface AugmentMeta {
  id: number;
  name: string;
  rarity: number | null;
  description: string | null;
  icon_path: string | null;
}

export interface ChampionMeta {
  id: number;
  key: string;
  name: string;
  title: string | null;
  tags: string[] | null;
  icon_path: string | null;
}

export interface ItemMeta {
  id: number;
  name: string;
  gold: number | null;
  tags: string[] | null;
  icon_path: string | null;
}
