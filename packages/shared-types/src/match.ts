export type MatchSource = "riot_api" | "lcu_upload";

/** Subset of Riot Match-V5 participant DTO (the fields we care about). */
export interface ParticipantDto {
  puuid: string;
  championId: number;
  championName: string;
  win: boolean;
  kills: number;
  deaths: number;
  assists: number;
  goldEarned: number;
  totalDamageDealtToChampions: number;
  totalDamageTaken: number;
  summoner1Id: number;
  summoner2Id: number;
  item0: number; item1: number; item2: number;
  item3: number; item4: number; item5: number; item6: number;
  // Arena
  playerSubteamId?: number;
  subteamPlacement?: number;
  placement?: number;
  playerAugment1?: number;
  playerAugment2?: number;
  playerAugment3?: number;
  playerAugment4?: number;
  playerAugment5?: number;
  playerAugment6?: number;
}

export interface MatchDto {
  metadata: { matchId: string; participants: string[] };
  info: {
    gameCreation: number;
    gameDuration: number;
    gameMode: string;
    gameVersion: string;
    platformId: string;
    queueId: number;
    participants: ParticipantDto[];
  };
}
