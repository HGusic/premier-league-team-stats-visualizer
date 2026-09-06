"use client";

import { useState } from "react";
import { RankPill, StatRadarProfile, type RadarMetric } from "./StatRadarProfile";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./DefenseSection.module.css";

const SET_PIECES_METRICS: readonly RadarMetric[] = [
  {
    name: "lostCorners",
    label: "Corners Conceded",
    shortLabel: "Conceded",
    invertScale: true,
  },
  { name: "wonCorners", label: "Corners Won", shortLabel: "Won" },
  {
    name: "penaltyGoalsConceded",
    label: "Penalty Goals Conceded",
    shortLabel: "Pen Goals",
    useRawValue: true,
    invertScale: true,
  },
  {
    name: "penaltyKickConceded",
    label: "Penalty Kick Conceded",
    shortLabel: "Pen Kicks",
    useRawValue: true,
    invertScale: true,
  },
];

const DISCIPLINE_METRICS: readonly RadarMetric[] = [
  {
    name: "foulsCommitted",
    label: "Fouls Committed",
    shortLabel: "Committed",
    invertScale: true,
  },
  {
    name: "foulsSuffered",
    label: "Fouls Suffered",
    shortLabel: "Suffered",
    invertScale: true,
  },
  {
    name: "redCards",
    label: "Red Cards",
    shortLabel: "Reds",
    useRawValue: true,
    invertScale: true,
  },
  {
    name: "yellowCards",
    label: "Yellow Cards",
    shortLabel: "Yellows",
    invertScale: true,
  },
];

type SetPiecesDisciplineSectionProps = {
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  teamAbbreviation?: string;
  profileRanks?: {
    setPieces?: number;
    discipline?: number;
    setPiecesDiscipline?: number;
  };
};

export function SetPiecesDisciplineSection({
  stats = [],
  aggregates = [],
  mode = "team",
  teamAbbreviation = "TEAM",
  profileRanks,
}: SetPiecesDisciplineSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const ranks = profileRanks ?? {};
  const sectionRank = mode === "team" ? ranks.setPiecesDiscipline ?? null : null;

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
          Set Pieces & Discipline
        </span>
        <span className={styles.toggleAction}>
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.radarRowPair}>
            <StatRadarProfile
              title="Set Pieces Profile"
              metrics={SET_PIECES_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#c05621"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.setPieces ?? null : null}
            />
            <StatRadarProfile
              title="Discipline Profile"
              metrics={DISCIPLINE_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#f07178"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.discipline ?? null : null}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
