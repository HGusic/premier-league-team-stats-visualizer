"use client";

import { useState } from "react";
import { RankPill, StatRadarProfile, type RadarMetric } from "./StatRadarProfile";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./DefenseSection.module.css";

const TACKLE_METRICS: readonly RadarMetric[] = [
  { name: "totalTackles", label: "Tackles", shortLabel: "Tackles" },
  { name: "inneffectiveTackles", label: "Tackles Lost", shortLabel: "Lost", invertScale: true },
  { name: "effectiveTackles", label: "Tackles Won", shortLabel: "Won" },
  { name: "tacklePct", label: "Tackle", shortLabel: "Tackle", useRawValue: true, isPercent: true },
];

const RECOVERY_METRICS: readonly RadarMetric[] = [
  { name: "totalClearance", label: "Clearances", shortLabel: "Clear" },
  { name: "defensiveActions", label: "Defensive Actions", shortLabel: "Actions" },
  { name: "interceptions", label: "Interceptions", shortLabel: "Int" },
  { name: "recoveries", label: "Recoveries", shortLabel: "Rec" },
];

const DEFENSIVE_METRICS: readonly RadarMetric[] = [
  { name: "shotsFaced", label: "Shots Faced", shortLabel: "Faced", invertScale: true },
  {
    name: "pointsAgainst",
    label: "Goals Against",
    shortLabel: "Against",
    source: "standings",
    invertScale: true,
  },
  { name: "cleanSheet", label: "Clean Sheets", shortLabel: "CS" },
  { name: "blockedShots", label: "Shots Blocked", shortLabel: "Blocked" },
];

const DUEL_METRICS: readonly RadarMetric[] = [
  { name: "duelsLost", label: "Duels Lost", shortLabel: "Lost", invertScale: true },
  { name: "duels", label: "Duels", shortLabel: "Duels" },
  { name: "duelWinPct", label: "Duel Win", shortLabel: "Win", useRawValue: true, isPercent: true },
  { name: "duelsWon", label: "Duels Won", shortLabel: "Won" },
];

type DefenseSectionProps = {
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  teamAbbreviation?: string;
  profileRanks?: {
    tackle?: number;
    recovery?: number;
    defensive?: number;
    duel?: number;
    defense?: number;
  };
};

export function DefenseSection({
  stats = [],
  aggregates = [],
  mode = "team",
  teamAbbreviation = "TEAM",
  profileRanks,
}: DefenseSectionProps) {
  const [expanded, setExpanded] = useState(true);
  const ranks = profileRanks ?? {};
  const sectionRank = mode === "team" ? ranks.defense ?? null : null;

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
          Defense
        </span>
        <span className={styles.toggleAction}>
          {expanded ? "Collapse" : "Expand"}
        </span>
      </button>

      {expanded ? (
        <div className={styles.body}>
          <div className={styles.radarRow}>
            <StatRadarProfile
              title="Defensive Profile"
              metrics={DEFENSIVE_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#a78bfa"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.defensive ?? null : null}
            />
            <StatRadarProfile
              title="Tackle Profile"
              metrics={TACKLE_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#c8102e"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.tackle ?? null : null}
            />
            <StatRadarProfile
              title="Duel Profile"
              metrics={DUEL_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#2fbf71"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.duel ?? null : null}
            />
            <StatRadarProfile
              title="Recovery Profile"
              metrics={RECOVERY_METRICS}
              stats={stats}
              aggregates={aggregates}
              mode={mode}
              accent="#3d9bff"
              teamAbbreviation={teamAbbreviation}
              profileRank={mode === "team" ? ranks.recovery ?? null : null}
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
