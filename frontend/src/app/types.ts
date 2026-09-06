export type Team = {
  espn_id: string;
  name: string;
  abbreviation: string;
  slug: string | null;
  league: string;
  logo_url: string | null;
  color: string | null;
  alternate_color: string | null;
};

export type TeamStat = {
  source: string;
  category: string;
  name: string;
  display_name: string;
  abbreviation: string | null;
  value: number | null;
  display_value: string | null;
  per_game_value: number | null;
  rank: number | null;
  rank_display_value: string | null;
};

export type LeagueAggregateStat = {
  source: string;
  category: string;
  name: string;
  display_name: string;
  abbreviation: string | null;
  team_count: number;
  avg_value: number | null;
  min_value: number | null;
  min_team_espn_id: string | null;
  min_team_name: string | null;
  max_value: number | null;
  max_team_espn_id: string | null;
  max_team_name: string | null;
  avg_per_game: number | null;
  min_per_game: number | null;
  min_per_game_team_espn_id: string | null;
  min_per_game_team_name: string | null;
  max_per_game: number | null;
  max_per_game_team_espn_id: string | null;
  max_per_game_team_name: string | null;
};

export type TeamProfile = {
  view?: "team" | "average";
  team: Team;
  season_year: number;
  snapshot: {
    id: number | null;
    season_year: number;
    season_type: number;
    ingested_at: string;
    source_count: number | null;
    stat_count?: number;
  } | null;
  stats: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  profile_ranks?: {
    tackle?: number;
    recovery?: number;
    defensive?: number;
    duel?: number;
    defense?: number;
    setPieces?: number;
    discipline?: number;
    setPiecesDiscipline?: number;
    shotStopping?: number;
    boxCommand?: number;
    facingPenalties?: number;
    goalkeeping?: number;
    ballControl?: number;
    ballSecurity?: number;
    possession?: number;
    crossing?: number;
    longBalls?: number;
    throughBalls?: number;
    chancePassing?: number;
    passing?: number;
    scoring?: number;
    shooting?: number;
    chanceCreation?: number;
    shotVariety?: number;
    offense?: number;
  };
  header?: {
    headline: string;
    team_name?: string | null;
    position: string | null;
    position_rank?: number | null;
    points: string | null;
    record: string | null;
  };
};
