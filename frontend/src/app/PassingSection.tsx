"use client";

import { useState } from "react";
import { RankPill, StatRadarProfile, type RadarMetric } from "./StatRadarProfile";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./DefenseSection.module.css";

const CROSSING_METRICS: readonly RadarMetric[] = [
  { name: "totalCrosses", label: "Crosses", shortLabel: "Crosses" },
  { name: "accurateCrosses", label: "Accurate Crosses", shortLabel: "Accurate" },
  {
    name: "inaccurateCrosses",
    label: "Inaccurate Crosses",
    shortLabel: "Inaccurate",
    invertScale: true,
  },
  {
    name: "crossPct",
    label: "Cross",
    shortLabel: "Cross",
    useRawValue: true,
    isPercent: true,
  },
];

const LONG_BALL_METRICS: readonly RadarMetric[] = [
  { name: "totalLongBalls", label: "Long Balls", shortLabel: "Long" },
  {
    name: "accurateLongBalls",
    label: "Accurate Long Balls",
    shortLabel: "Accurate",
  },
  {
    name: "inaccurateLongBalls",
    label: "Inaccurate Long Balls",
    shortLabel: "Inaccurate",
    invertScale: true,
  },
  {
    name: "longballPct",
    label: "Long Ball",
    shortLabel: "LB",
    useRawValue: true,
    isPercent: true,
  },
];

const THROUGH_BALL_METRICS: readonly RadarMetric[] = [
  { name: "totalThroughBalls", label: "Through Balls", shortLabel: "Through" },
  {
    name: "accurateThroughBalls",
    label: "Accurate Through Balls",
    shortLabel: "Accurate",
  },
  {
    name: "inaccurateThroughBalls",
    label: "Inaccurate Through Balls",
    shortLabel: "Inaccurate",
    invertScale: true,
  },
  {
    name: "throughBallPct",
    label: "Through Ball",
    shortLabel: "TB",
    useRawValue: true,
    isPercent: true,
  },
];

const CHANCE_PASSING_METRICS: readonly RadarMetric[] = [
  { name: "shotAssists", label: "Shot Assists", shortLabel: "Shot Ast" },
  { name: "goalAssists", label: "Assists", shortLabel: "Assists" },
  {
    name: "bigChanceCreated",
    label: "Big Chances Created",
    shortLabel: "Big Chances",
  },
  {
    name: "avgExpectedGoals",
    label: "xG",
    shortLabel: "xG",
    useRawValue: true,
  },
];

type PassingSectionProps = {
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  teamAbbreviation?: string;
  profileRanks?: {
    crossing?: number;
    longBalls?: number;
    throughBalls?: number;
    chancePassing?: number;
    passing?: number;
  };
};

export function PassingSection({
  stats = [],
  aggregates = [],
  mode = "team",
  teamAbbreviation = "TEAM",
  profileRanks,
}: PassingSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const ranks = profileRanks ?? {};
  const sectionRank = mode === "team" ? ranks.passing ?? null : null;

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
          Passing
        </span>
        <span className={styles.toggleAction}>
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.radarRow}>
            <StatRadarProfile
              title="Crossing Profile"
              metrics={CROSSING_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#63b3ed"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.crossing ?? null : null}
            />
            <StatRadarProfile
              title="Long Balls Profile"
              metrics={LONG_BALL_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#d69e2e"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.longBalls ?? null : null}
            />
            <StatRadarProfile
              title="Through Balls Profile"
              metrics={THROUGH_BALL_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#667eea"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.throughBalls ?? null : null}
            />
            <StatRadarProfile
              title="Chance Creation Profile"
              metrics={CHANCE_PASSING_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#dd6b20"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.chancePassing ?? null : null}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
