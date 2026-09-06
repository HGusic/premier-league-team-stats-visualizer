"use client";

import { useState } from "react";
import { RankPill, StatRadarProfile, type RadarMetric } from "./StatRadarProfile";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./DefenseSection.module.css";

const SHOT_STOPPING_METRICS: readonly RadarMetric[] = [
  { name: "saves", label: "Saves", shortLabel: "Saves" },
  {
    name: "savePct",
    label: "Save",
    shortLabel: "Save",
    useRawValue: true,
    isPercent: true,
  },
  { name: "bigChanceSaves", label: "Big Chance Saves", shortLabel: "BC Saves" },
  {
    name: "pointsAgainst",
    label: "Goals Against",
    shortLabel: "Against",
    source: "standings",
    invertScale: true,
  },
];

const BOX_COMMAND_METRICS: readonly RadarMetric[] = [
  { name: "punches", label: "Punches", shortLabel: "Punches" },
  { name: "smothers", label: "Smothers", shortLabel: "Smothers" },
  { name: "crossesCaught", label: "Crosses Claimed", shortLabel: "Claimed" },
];

const FACING_PENALTIES_METRICS: readonly RadarMetric[] = [
  {
    name: "penaltyKickConceded",
    label: "Penalties Faced",
    shortLabel: "Faced",
    useRawValue: true,
    invertScale: true,
  },
  {
    name: "penaltyKicksSaved",
    label: "Penalties Saved",
    shortLabel: "Saved",
    useRawValue: true,
  },
  {
    name: "penaltyKickSavePct",
    label: "Penalty Save",
    shortLabel: "Pen Save",
    useRawValue: true,
    isPercent: true,
  },
  {
    name: "penaltyGoalsConceded",
    label: "Penalty Goals Conceded",
    shortLabel: "Pen Goals",
    useRawValue: true,
    invertScale: true,
  },
];

type GoalkeepingSectionProps = {
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  teamAbbreviation?: string;
  profileRanks?: {
    shotStopping?: number;
    boxCommand?: number;
    facingPenalties?: number;
    goalkeeping?: number;
  };
};

export function GoalkeepingSection({
  stats = [],
  aggregates = [],
  mode = "team",
  teamAbbreviation = "TEAM",
  profileRanks,
}: GoalkeepingSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const ranks = profileRanks ?? {};
  const sectionRank = mode === "team" ? ranks.goalkeeping ?? null : null;

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
          Goalkeeping
        </span>
        <span className={styles.toggleAction}>
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.radarRowTriple}>
            <StatRadarProfile
              title="Shot Stopping Profile"
              metrics={SHOT_STOPPING_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#5ec8e6"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.shotStopping ?? null : null}
            />
            <StatRadarProfile
              title="Box Command Profile"
              metrics={BOX_COMMAND_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#ed8936"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.boxCommand ?? null : null}
            />
            <StatRadarProfile
              title="Facing Penalties Profile"
              metrics={FACING_PENALTIES_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#805ad5"
              teamAbbreviation={teamAbbreviation}
              profileRank={
                mode === "team" ? ranks.facingPenalties ?? null : null
              }
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
