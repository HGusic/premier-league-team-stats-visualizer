"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { LeagueAggregateStat, TeamStat } from "./types";
import styles from "./StatRadarProfile.module.css";

export type RadarMetric = {
  name: string;
  label: string;
  shortLabel: string;
  /** Stat source bucket; defaults to core_statistics. */
  source?: string;
  /** Use season/true value (not per-game) for axis label and 0→max scaling. */
  useRawValue?: boolean;
  /** Format raw value as a percentage (0–1 ESPN fractions or 0–100). */
  isPercent?: boolean;
  /** Lower values are better; radar fill grows as value approaches 0. */
  invertScale?: boolean;
};

type RadarPoint = {
  metric: string;
  label: string;
  shortLabel: string;
  scaleScore: number;
  perGame: number | null;
  value: number | null;
  rank: number | null;
  min: number | null;
  max: number | null;
  minTeam: string | null;
  maxTeam: string | null;
  leagueAvg: number | null;
  leagueAvgPerGame: number | null;
  useRawValue: boolean;
  isPercent: boolean;
  axisDisplay: string;
};

function formatRawStat(value: number | null, isPercent = false): string {
  if (value == null) return "—";
  if (isPercent) {
    // ESPN stores many % stats as 0–1 fractions.
    if (value >= 0 && value <= 1) {
      return `${(value * 100).toFixed(1)}%`;
    }
    return `${value.toFixed(1)}%`;
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatStatNumber(value: number | null): string {
  if (value == null) return "—";
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

/** Strip trailing % from metric names so we don't show "63.7% Possession %". */
function displayLabel(label: string): string {
  return label.replace(/\s*%+\s*$/g, "").trim();
}

function formatLegendPrimary(point: {
  useRawValue: boolean;
  isPercent: boolean;
  perGame: number | null;
  value: number | null;
}): string {
  if (point.isPercent) {
    return formatRawStat(point.value, true);
  }
  if (point.useRawValue) {
    return formatRawStat(point.value, false);
  }
  return formatStatNumber(point.perGame);
}

function formatAxisValue(point: {
  useRawValue: boolean;
  isPercent: boolean;
  perGame: number | null;
  value: number | null;
}): string {
  if (point.isPercent) {
    return formatRawStat(point.value, true);
  }
  if (point.useRawValue) {
    return formatRawStat(point.value, false);
  }
  return formatStatNumber(point.perGame);
}

function isPerGamePoint(point: {
  useRawValue: boolean;
  isPercent: boolean;
}): boolean {
  return !point.useRawValue && !point.isPercent;
}

function formatOrdinal(rank: number | null): string | null {
  if (rank == null || rank < 1) return null;
  const mod100 = rank % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${rank}th`;
  switch (rank % 10) {
    case 1:
      return `${rank}st`;
    case 2:
      return `${rank}nd`;
    case 3:
      return `${rank}rd`;
    default:
      return `${rank}th`;
  }
}

function rankToneClass(rank: number | null): string {
  if (rank == null || rank < 1) return "";
  if (rank === 1) return styles.rankGold;
  if (rank <= 5) return styles.rankDarkGreen;
  if (rank <= 10) return styles.rankLightGreen;
  if (rank <= 14) return styles.rankYellow;
  if (rank <= 17) return styles.rankOrange;
  return styles.rankRed;
}

export function RankPill({
  rank,
  className,
}: {
  rank: number | null | undefined;
  className?: string;
}) {
  const ordinal = formatOrdinal(rank ?? null);
  if (!ordinal || rank == null) return null;
  return (
    <span
      className={[styles.rankPill, rankToneClass(rank), className]
        .filter(Boolean)
        .join(" ")}
    >
      {ordinal}
    </span>
  );
}

function compareOp(teamValue: number | null, leagueValue: number | null): string {
  if (teamValue == null || leagueValue == null) return "=";
  const delta = teamValue - leagueValue;
  if (Math.abs(delta) < 0.005) return "=";
  return delta > 0 ? ">" : "<";
}

function formatLeagueCompare(point: {
  useRawValue: boolean;
  isPercent: boolean;
  perGame: number | null;
  value: number | null;
  leagueAvg: number | null;
  leagueAvgPerGame: number | null;
}, teamAbbreviation: string): string {
  const abbr = teamAbbreviation || "TEAM";
  if (point.useRawValue) {
    const team = formatRawStat(point.value, point.isPercent);
    const league = formatRawStat(point.leagueAvg, point.isPercent);
    const op = compareOp(point.value, point.leagueAvg);
    return `${abbr} ${team} ${op} LEAG ${league}`;
  }

  const teamVal = point.perGame;
  const leagueVal = point.leagueAvgPerGame;
  const op = compareOp(teamVal, leagueVal);
  return `${abbr} ${formatStatNumber(teamVal)} /g ${op} LEAG ${formatStatNumber(leagueVal)} /g`;
}

/** Map a value onto 0–100 from zero up to league max. */
function zeroToMaxScale(
  value: number | null,
  max: number | null,
  invert = false,
): number {
  if (value == null || max == null) return 0;
  if (max <= 0) return value > 0 ? (invert ? 0 : 100) : invert ? 100 : 0;
  const ratio = Math.min(1, Math.max(0, value / max));
  const score = (invert ? 1 - ratio : ratio) * 100;
  return Math.round(score * 100) / 100;
}

function findStat(
  stats: TeamStat[],
  name: string,
  source = "core_statistics",
): TeamStat | undefined {
  return stats.find((stat) => stat.source === source && stat.name === name);
}

function resolveGamesPlayed(stats: TeamStat[]): number | null {
  const preferredSources = ["standings", "team_record", "core_statistics"];
  for (const source of preferredSources) {
    for (const name of ["gamesPlayed", "appearances"]) {
      const row = stats.find(
        (stat) => stat.source === source && stat.name === name,
      );
      if (row?.value != null && row.value > 0) {
        return row.value;
      }
    }
  }
  return null;
}

function resolvePerGameValue(
  stat: TeamStat | undefined,
  stats: TeamStat[],
): number | null {
  if (stat?.per_game_value != null) {
    return stat.per_game_value;
  }
  if (stat?.value == null) {
    return null;
  }
  const gamesPlayed = resolveGamesPlayed(stats);
  if (gamesPlayed == null || gamesPlayed <= 0) {
    return null;
  }
  return Math.round((stat.value / gamesPlayed) * 100) / 100;
}

function findAggregate(
  aggregates: LeagueAggregateStat[],
  name: string,
  source = "core_statistics",
): LeagueAggregateStat | undefined {
  return aggregates.find(
    (stat) => stat.source === source && stat.name === name,
  );
}

function pickScaleFields(agg: LeagueAggregateStat | undefined, preferPerGame: boolean) {
  if (!agg) {
    return {
      min: null as number | null,
      max: null as number | null,
      minTeam: null as string | null,
      maxTeam: null as string | null,
    };
  }
  if (
    preferPerGame &&
    (agg.min_per_game != null || agg.max_per_game != null)
  ) {
    return {
      min: agg.min_per_game,
      max: agg.max_per_game,
      minTeam: agg.min_per_game_team_name,
      maxTeam: agg.max_per_game_team_name,
    };
  }
  return {
    min: agg.min_value,
    max: agg.max_value,
    minTeam: agg.min_team_name,
    maxTeam: agg.max_team_name,
  };
}

type StatRadarProfileProps = {
  title: string;
  metrics: readonly RadarMetric[];
  stats?: TeamStat[];
  aggregates?: LeagueAggregateStat[];
  mode?: "team" | "average";
  accent?: string;
  teamAbbreviation?: string;
  profileRank?: number | null;
};

export function StatRadarProfile({
  title,
  metrics,
  stats = [],
  aggregates = [],
  mode = "team",
  accent = "#c8102e",
  teamAbbreviation = "TEAM",
  profileRank = null,
}: StatRadarProfileProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(360);

  useEffect(() => {
    const node = wrapRef.current;
    if (!node) return;

    const update = (nextWidth: number) => {
      setWidth(Math.max(0, Math.floor(nextWidth)));
    };

    update(node.getBoundingClientRect().width);

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) update(entry.contentRect.width);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const compact = width < 340;
  const chartHeight = compact ? 250 : width < 420 ? 280 : 310;
  const outerRadius = compact ? "72%" : "78%";
  const chartMargin = compact
    ? { top: 6, right: 8, bottom: 0, left: 8 }
    : { top: 8, right: 12, bottom: 0, left: 12 };

  const data = useMemo((): RadarPoint[] => {
    return metrics.map((metric) => {
      const source = metric.source ?? "core_statistics";
      const agg = findAggregate(aggregates, metric.name, source);
      const useRawValue = Boolean(metric.useRawValue);
      const isPercent = Boolean(metric.isPercent);
      const invertScale = Boolean(metric.invertScale);

      if (mode === "average") {
        const preferPerGame = !useRawValue;
        const bounds = pickScaleFields(agg, preferPerGame);
        const value = preferPerGame
          ? agg?.avg_per_game ?? agg?.avg_value ?? null
          : agg?.avg_value ?? null;
        return {
          metric: metric.name,
          label: metric.label,
          shortLabel: metric.shortLabel,
          scaleScore: zeroToMaxScale(value, bounds.max, invertScale),
          perGame: agg?.avg_per_game ?? null,
          value: agg?.avg_value ?? null,
          rank: null,
          min: bounds.min,
          max: bounds.max,
          minTeam: bounds.minTeam,
          maxTeam: bounds.maxTeam,
          leagueAvg: agg?.avg_value ?? null,
          leagueAvgPerGame: agg?.avg_per_game ?? null,
          useRawValue,
          isPercent,
          axisDisplay: formatAxisValue({
            useRawValue,
            isPercent,
            perGame: agg?.avg_per_game ?? null,
            value: agg?.avg_value ?? null,
          }),
        };
      }

      const stat = findStat(stats, metric.name, source);
      const preferPerGame = !useRawValue;
      const scaleBounds = pickScaleFields(agg, preferPerGame);
      const perGame = resolvePerGameValue(stat, stats);
      const scaleValue = preferPerGame
        ? perGame ?? stat?.value ?? null
        : stat?.value ?? null;

      return {
        metric: metric.name,
        label: metric.label,
        shortLabel: metric.shortLabel,
        scaleScore: zeroToMaxScale(scaleValue, scaleBounds.max, invertScale),
        perGame,
        value: stat?.value ?? null,
        rank: stat?.rank ?? null,
        min: scaleBounds.min,
        max: scaleBounds.max,
        minTeam: scaleBounds.minTeam,
        maxTeam: scaleBounds.maxTeam,
        leagueAvg: agg?.avg_value ?? null,
        leagueAvgPerGame: agg?.avg_per_game ?? null,
        useRawValue,
        isPercent,
        axisDisplay: formatAxisValue({
          useRawValue,
          isPercent,
          perGame,
          value: stat?.value ?? null,
        }),
      };
    });
  }, [aggregates, metrics, mode, stats]);

  const hasData = data.some(
    (point) => point.scaleScore > 0 || point.value != null || point.perGame != null,
  );

  if (!hasData) {
    return (
      <div className={styles.card}>
        <h3 className={styles.title}>
          {profileRank != null ? (
            <>
              <span className={`${styles.rankPill} ${rankToneClass(profileRank)}`}>
                {formatOrdinal(profileRank)}
              </span>{" "}
            </>
          ) : null}
          {title}
        </h3>
        <p className={styles.empty}>Stats unavailable for this snapshot.</p>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <h3 className={styles.title}>
        {profileRank != null ? (
          <>
            <span className={`${styles.rankPill} ${rankToneClass(profileRank)}`}>
              {formatOrdinal(profileRank)}
            </span>{" "}
          </>
        ) : null}
        {title}
      </h3>

      <div className={styles.chartWrap} ref={wrapRef}>
        <ResponsiveContainer width="100%" height={chartHeight}>
          <RadarChart
            data={data}
            cx="50%"
            cy="50%"
            outerRadius={outerRadius}
            margin={chartMargin}
          >
            <PolarGrid stroke="rgba(238, 242, 246, 0.15)" />
            <PolarAngleAxis
              dataKey="label"
              tick={(props) => (
                <AngleTick {...props} data={data} compact={compact} />
              )}
              tickLine={false}
            />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
            <Radar
              name="0–max scale"
              dataKey="scaleScore"
              stroke={accent}
              fill={accent}
              fillOpacity={0.45}
              strokeWidth={2}
              isAnimationActive
            />
            <Tooltip content={<RadarTooltip mode={mode} />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <ul className={styles.legend}>
        {data.map((point) => {
          const ordinal = formatOrdinal(point.rank);
          const primary = formatLegendPrimary(point);
          const label = displayLabel(point.label);
          const compareLine =
            mode === "average"
              ? `LEAG ${
                  point.useRawValue || point.isPercent
                    ? formatRawStat(point.leagueAvg, point.isPercent)
                    : point.leagueAvgPerGame != null
                      ? `${formatStatNumber(point.leagueAvgPerGame)} /g`
                      : "—"
                }`
              : formatLeagueCompare(point, teamAbbreviation);
          return (
            <li key={point.metric}>
              <strong className={styles.statHeading}>
                {ordinal ? (
                  <>
                    <span className={`${styles.rankPill} ${rankToneClass(point.rank)}`}>
                      {ordinal}
                    </span>{" "}
                  </>
                ) : null}
                {primary} {label}
              </strong>
              <span className={styles.compare}>{compareLine}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

type AngleTickProps = {
  data: RadarPoint[];
  compact?: boolean;
  x?: number | string;
  y?: number | string;
  cx?: number | string;
  cy?: number | string;
  payload?: { value: string };
};

function AngleTick({
  data,
  compact = false,
  x = 0,
  y = 0,
  cx = 0,
  cy = 0,
  payload,
}: AngleTickProps) {
  const point = data.find((row) => row.label === payload?.value);
  const label = displayLabel(point?.label ?? payload?.value ?? "");
  const words = label.trim().split(/\s+/).filter(Boolean);
  const valueLabel = point?.axisDisplay ?? "—";

  const px = Number(x);
  const py = Number(y);
  const centerX = Number(cx);
  const centerY = Number(cy);
  const dx = px - centerX;
  const dy = py - centerY;
  const dist = Math.hypot(dx, dy) || 1;
  const push = compact ? 10 : 16;
  const ox = px + (dx / dist) * push;
  const oy = py + (dy / dist) * push;

  // Top/bottom labels stay on one line; left/right wrap one word per line.
  const isSideLabel = Math.abs(dx) > Math.abs(dy);
  const nameLines = isSideLabel ? words : [words.join(" ")].filter(Boolean);

  const lineHeight = compact ? 10 : 12;
  const nameStartDy =
    nameLines.length > 1 ? (compact ? -8 : -10) : compact ? -2 : -4;
  const valueDy = nameStartDy + nameLines.length * lineHeight + (compact ? 2 : 3);

  return (
    <g transform={`translate(${ox},${oy})`}>
      <text
        textAnchor="middle"
        fill="rgba(238, 242, 246, 0.92)"
        fontSize={compact ? 9 : 11}
      >
        {nameLines.map((line, index) => (
          <tspan key={`${line}-${index}`} x={0} dy={index === 0 ? nameStartDy : lineHeight}>
            {line}
          </tspan>
        ))}
      </text>
      <text
        textAnchor="middle"
        fill="rgba(238, 242, 246, 0.55)"
        fontSize={compact ? 8 : 10}
        dy={valueDy}
      >
        {valueLabel}
      </text>
    </g>
  );
}

type TooltipProps = {
  active?: boolean;
  payload?: Array<{ payload: RadarPoint }>;
  mode?: "team" | "average";
};

function RadarTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipTitle}>{displayLabel(point.label)}</div>
      {point.isPercent ? (
        <div>Value: {formatRawStat(point.value, true)}</div>
      ) : point.useRawValue ? (
        <div>Total: {formatRawStat(point.value, false)}</div>
      ) : (
        <div>Per game: {point.perGame != null ? `${formatStatNumber(point.perGame)} /g` : "—"}</div>
      )}
      {!point.useRawValue && !point.isPercent ? (
        <div>
          Total:{" "}
          {point.value != null ? formatStatNumber(point.value) : "—"}
        </div>
      ) : null}
      <div>
        League avg:{" "}
        {point.isPercent || point.useRawValue
          ? formatRawStat(point.leagueAvg, point.isPercent)
          : point.leagueAvgPerGame != null
            ? `${formatStatNumber(point.leagueAvgPerGame)} /g`
            : point.leagueAvg != null
              ? formatStatNumber(point.leagueAvg)
              : "—"}
      </div>
      <div>Radar fill: {point.scaleScore.toFixed(0)} / 100</div>
    </div>
  );
}
