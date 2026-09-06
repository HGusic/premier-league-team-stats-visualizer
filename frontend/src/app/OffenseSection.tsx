"use client";

import { useState } from "react";
import { RankPill, StatRadarProfile, type RadarMetric } from "./StatRadarProfile";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./DefenseSection.module.css";

const SCORING_METRICS: readonly RadarMetric[] = [
  { name: "totalGoals", label: "Goals", shortLabel: "Goals" },
  { name: "goalAssists", label: "Assists", shortLabel: "Assists" },
  {
    name: "gameWinningGoals",
    label: "Game Winning Goals",
    shortLabel: "GWG",
  },
  {
    name: "goalConversion",
    label: "Conversion",
    shortLabel: "Conv",
    useRawValue: true,
    isPercent: true,
  },
];

const SHOOTING_METRICS: readonly RadarMetric[] = [
  { name: "totalShots", label: "Shots", shortLabel: "Shots" },
  { name: "shotsOnTarget", label: "Shots On Target", shortLabel: "On Target" },
  {
    name: "shotsOffTarget",
    label: "Shots Off Target",
    shortLabel: "Off Target",
    invertScale: true,
  },
  {
    name: "shotPct",
    label: "Shot",
    shortLabel: "Shot",
    useRawValue: true,
    isPercent: true,
  },
];

const CHANCE_CREATION_METRICS: readonly RadarMetric[] = [
  {
    name: "bigChanceCreated",
    label: "Big Chances Created",
    shortLabel: "Big Chances",
  },
  { name: "shotAssists", label: "Shot Assists", shortLabel: "Shot Ast" },
  {
    name: "avgExpectedGoals",
    label: "xG",
    shortLabel: "xG",
    useRawValue: true,
  },
  { name: "headedGoals", label: "Headed Goals", shortLabel: "Headers" },
];

const SHOT_VARIETY_METRICS: readonly RadarMetric[] = [
  {
    name: "leftFootedShots",
    label: "Left Footed Shots",
    shortLabel: "Left",
  },
  {
    name: "rightFootedShots",
    label: "Right Footed Shots",
    shortLabel: "Right",
  },
  { name: "freeKickGoals", label: "Free Kick Goals", shortLabel: "FK Goals" },
  {
    name: "penaltyKickGoals",
    label: "Penalty Goals",
    shortLabel: "Pens",
  },
];

type OffenseSectionProps = {
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  teamAbbreviation?: string;
  profileRanks?: {
    scoring?: number;
    shooting?: number;
    chanceCreation?: number;
    shotVariety?: number;
    offense?: number;
  };
};

export function OffenseSection({
  stats = [],
  aggregates = [],
  mode = "team",
  teamAbbreviation = "TEAM",
  profileRanks,
}: OffenseSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const ranks = profileRanks ?? {};
  const sectionRank = mode === "team" ? ranks.offense ?? null : null;

  return (
    <section className={styles.section}>
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={expanded}
        onClick={() => setExpanded((open) => !open)}
      >
        <span className={styles.toggleIcon} aria-hidden>
          {expanded ? "▾" : "▸"}
        </span>
        <span className={styles.toggleTitle}>
          {sectionRank != null ? (
            <>
              <RankPill rank={sectionRank} />{" "}
            </>
          ) : null}
          Offense
        </span>
        <span className={styles.toggleAction}>
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.radarRow}>
            <StatRadarProfile
              title="Scoring Profile"
              metrics={SCORING_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#e53e3e"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.scoring ?? null : null}
            />
            <StatRadarProfile
              title="Shooting Profile"
              metrics={SHOOTING_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#d53f8c"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.shooting ?? null : null}
            />
            <StatRadarProfile
              title="Chance Creation Profile"
              metrics={CHANCE_CREATION_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#f6ad55"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.chanceCreation ?? null : null}
            />
            <StatRadarProfile
              title="Shot Variety Profile"
              metrics={SHOT_VARIETY_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#9b2c2c"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.shotVariety ?? null : null}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
