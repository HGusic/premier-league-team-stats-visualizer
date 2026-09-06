"use client";

import { useState } from "react";
import { RankPill, StatRadarProfile, type RadarMetric } from "./StatRadarProfile";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./DefenseSection.module.css";

const BALL_CONTROL_METRICS: readonly RadarMetric[] = [
  {
    name: "possessionPct",
    label: "Possession",
    shortLabel: "Poss",
    useRawValue: true,
    isPercent: true,
  },
  { name: "totalPasses", label: "Passes", shortLabel: "Passes" },
  { name: "accuratePasses", label: "Accurate Passes", shortLabel: "Accurate" },
  {
    name: "passPct",
    label: "Pass",
    shortLabel: "Pass",
    useRawValue: true,
    isPercent: true,
  },
];

const BALL_SECURITY_METRICS: readonly RadarMetric[] = [
  {
    name: "inaccuratePasses",
    label: "Inaccurate Passes",
    shortLabel: "Inaccurate",
    invertScale: true,
  },
  {
    name: "timesTackled",
    label: "Times Tackled",
    shortLabel: "Tackled",
    invertScale: true,
  },
  { name: "recoveries", label: "Recoveries", shortLabel: "Rec" },
  { name: "duelsWon", label: "Duels Won", shortLabel: "Duels Won" },
];

type PossessionSectionProps = {
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  teamAbbreviation?: string;
  profileRanks?: {
    ballControl?: number;
    ballSecurity?: number;
    possession?: number;
  };
};

export function PossessionSection({
  stats = [],
  aggregates = [],
  mode = "team",
  teamAbbreviation = "TEAM",
  profileRanks,
}: PossessionSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const ranks = profileRanks ?? {};
  const sectionRank = mode === "team" ? ranks.possession ?? null : null;

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
          Possession
        </span>
        <span className={styles.toggleAction}>
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.radarRowPair}>
            <StatRadarProfile
              title="Ball Control Profile"
              metrics={BALL_CONTROL_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#4fd1c5"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.ballControl ?? null : null}
            />
            <StatRadarProfile
              title="Ball Security Profile"
              metrics={BALL_SECURITY_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#68d391"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.ballSecurity ?? null : null}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
