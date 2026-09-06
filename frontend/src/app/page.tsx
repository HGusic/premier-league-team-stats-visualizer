"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { DefenseSection } from "./DefenseSection";
import { GoalkeepingSection } from "./GoalkeepingSection";
import { OffenseSection } from "./OffenseSection";
import { PassingSection } from "./PassingSection";
import { PossessionSection } from "./PossessionSection";
import { SetPiecesDisciplineSection } from "./SetPiecesDisciplineSection";
import { RankPill } from "./StatRadarProfile";
import { TeamBar } from "./TeamBar";
import type { Team, TeamProfile } from "./types";
import styles from "./page.module.css";

// Same-origin by default (Next.js rewrites /api → backend) so localhost and 127.0.0.1 both work.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const AVERAGE_ID = "__average__";
const BETA_NOTICE_KEY = "pl-stats-beta-notice-seen";
const MENU_ITEMS = ["Team Profile"] as const;
type MenuItem = (typeof MENU_ITEMS)[number];

export default function Home() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>("364");
  const [activeMenu, setActiveMenu] = useState<MenuItem>("Team Profile");
  const [profile, setProfile] = useState<TeamProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tableExpanded, setTableExpanded] = useState(true);
  const [showBetaNotice, setShowBetaNotice] = useState(false);

  const isAverageView = selectedTeamId === AVERAGE_ID;

  const selectedTeam = useMemo(() => {
    if (isAverageView) {
      return {
        espn_id: AVERAGE_ID,
        name: "League Average",
        abbreviation: "AVG",
        slug: "league-average",
        league: "eng.1",
        logo_url: null,
        color: "3d5a80",
        alternate_color: null,
      } satisfies Team;
    }
    return teams.find((team) => team.espn_id === selectedTeamId) ?? null;
  }, [isAverageView, selectedTeamId, teams]);

  const teamColorHex = useMemo(() => {
    const raw = selectedTeam?.color?.trim().replace(/^#/, "") ?? "";
    if (/^[0-9a-fA-F]{6}$/.test(raw) || /^[0-9a-fA-F]{3}$/.test(raw)) {
      return `#${raw}`;
    }
    return "#c8102e";
  }, [selectedTeam]);

  const loadTeams = useCallback(async () => {
    const response = await fetch(`${API_BASE}/api/teams`);
    if (!response.ok) {
      throw new Error(`Failed to load teams (${response.status})`);
    }
    const data = (await response.json()) as { teams: Team[] };
    setTeams(data.teams);
    if (data.teams.length > 0) {
      setSelectedTeamId((current) => {
        if (current === AVERAGE_ID) return current;
        return data.teams.some((team) => team.espn_id === current)
          ? current
          : data.teams[0].espn_id;
      });
    }
  }, []);

  const loadProfile = useCallback(async (teamId: string) => {
    setLoading(true);
    setError(null);
    try {
      const url =
        teamId === AVERAGE_ID
          ? `${API_BASE}/api/league/average-profile?season_year=2026`
          : `${API_BASE}/api/teams/${teamId}/profile?season_year=2026`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to load profile (${response.status})`);
      }
      const data = (await response.json()) as TeamProfile;
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTeams().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load teams");
    });
  }, [loadTeams]);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(BETA_NOTICE_KEY) !== "1") {
        setShowBetaNotice(true);
      }
    } catch {
      setShowBetaNotice(true);
    }
  }, []);

  const dismissBetaNotice = useCallback(() => {
    try {
      window.localStorage.setItem(BETA_NOTICE_KEY, "1");
    } catch {
      // Ignore storage failures; still close for this session.
    }
    setShowBetaNotice(false);
  }, []);

  useEffect(() => {
    if (activeMenu === "Team Profile") {
      loadProfile(selectedTeamId).catch(() => undefined);
    }
  }, [activeMenu, loadProfile, selectedTeamId]);

  const hasContent =
    !loading &&
    profile &&
    ((isAverageView && (profile.aggregates?.length ?? 0) > 0) ||
      (!isAverageView && profile.stats.length > 0));

  return (
    <div
      className={styles.shell}
      style={{ ["--team-color" as string]: teamColorHex }}
    >
      {showBetaNotice ? (
        <div className={styles.betaOverlay} role="presentation">
          <div
            className={styles.betaDialog}
            role="dialog"
            aria-modal="true"
            aria-labelledby="beta-notice-title"
          >
            <p id="beta-notice-title" className={styles.betaBody}>
              This is a BETA! Data and Visualizations and Rank Normalization
              could be incorrect.
            </p>
            <button
              type="button"
              className={styles.betaButton}
              onClick={dismissBetaNotice}
            >
              I understand
            </button>
          </div>
        </div>
      ) : null}

      <TeamBar
        teams={teams}
        selectedTeamId={selectedTeamId}
        isAverageView={isAverageView}
        onSelectAverage={() => setSelectedTeamId(AVERAGE_ID)}
        onSelectTeam={setSelectedTeamId}
      />

      <nav className={styles.menuBar}>
        {MENU_ITEMS.map((item) => {
          const active = item === activeMenu;
          return (
            <button
              key={item}
              type="button"
              className={`${styles.menuItem} ${active ? styles.menuItemActive : ""}`}
              onClick={() => setActiveMenu(item)}
            >
              {item}
            </button>
          );
        })}
      </nav>

      <main className={styles.main}>
        {activeMenu === "Team Profile" ? (
          <section className={styles.panel}>
            <div className={styles.panelHeader}>
              <div>
                <h1 className={styles.title}>
                  {profile?.header ? (
                    <>
                      <span className={styles.titleChip}>
                        {profile.header.team_name ??
                          selectedTeam?.name ??
                          "Team"}
                      </span>
                      {profile.header.position_rank != null ? (
                        <RankPill
                          rank={profile.header.position_rank}
                          className={styles.titleRank}
                        />
                      ) : (
                        <span className={styles.titleChip}>
                          {profile.header.position ?? "—"}
                        </span>
                      )}
                      <span className={styles.titleChip}>
                        {profile.header.points ?? "—"}
                      </span>
                      <span className={styles.titleChip}>
                        {profile.header.record ?? "—"}
                      </span>
                    </>
                  ) : (
                    <span className={styles.titleChip}>
                      {isAverageView
                        ? "League Average"
                        : (selectedTeam?.name ?? "Team")}
                    </span>
                  )}
                </h1>
                {!profile?.header && !profile?.snapshot ? (
                  <p className={styles.subtitle}>
                    No snapshot yet. Run the backend ingest CLI to load stats
                    and ranks.
                  </p>
                ) : null}
              </div>
            </div>

            {error ? <p className={styles.error}>{error}</p> : null}
            {loading ? <p className={styles.muted}>Loading snapshot…</p> : null}

            {hasContent && profile ? (
              <>
                <DefenseSection
                  mode={isAverageView ? "average" : "team"}
                  stats={profile.stats}
                  aggregates={profile.aggregates}
                  profileRanks={profile.profile_ranks}
                  teamAbbreviation={
                    isAverageView
                      ? "LEAG"
                      : selectedTeam?.abbreviation ?? profile.team.abbreviation
                  }
                />
                <OffenseSection
                  mode={isAverageView ? "average" : "team"}
                  stats={profile.stats}
                  aggregates={profile.aggregates}
                  profileRanks={profile.profile_ranks}
                  teamAbbreviation={
                    isAverageView
                      ? "LEAG"
                      : selectedTeam?.abbreviation ?? profile.team.abbreviation
                  }
                />
                <PossessionSection
                  mode={isAverageView ? "average" : "team"}
                  stats={profile.stats}
                  aggregates={profile.aggregates}
                  profileRanks={profile.profile_ranks}
                  teamAbbreviation={
                    isAverageView
                      ? "LEAG"
                      : selectedTeam?.abbreviation ?? profile.team.abbreviation
                  }
                />
                <PassingSection
                  mode={isAverageView ? "average" : "team"}
                  stats={profile.stats}
                  aggregates={profile.aggregates}
                  profileRanks={profile.profile_ranks}
                  teamAbbreviation={
                    isAverageView
                      ? "LEAG"
                      : selectedTeam?.abbreviation ?? profile.team.abbreviation
                  }
                />
                <GoalkeepingSection
                  mode={isAverageView ? "average" : "team"}
                  stats={profile.stats}
                  aggregates={profile.aggregates}
                  profileRanks={profile.profile_ranks}
                  teamAbbreviation={
                    isAverageView
                      ? "LEAG"
                      : selectedTeam?.abbreviation ?? profile.team.abbreviation
                  }
                />
                <SetPiecesDisciplineSection
                  mode={isAverageView ? "average" : "team"}
                  stats={profile.stats}
                  aggregates={profile.aggregates}
                  profileRanks={profile.profile_ranks}
                  teamAbbreviation={
                    isAverageView
                      ? "LEAG"
                      : selectedTeam?.abbreviation ?? profile.team.abbreviation
                  }
                />

                <div className={styles.tableSection}>
                  <button
                    type="button"
                    className={styles.tableToggle}
                    aria-expanded={tableExpanded}
                    onClick={() => setTableExpanded((open) => !open)}
                  >
                    <span className={styles.tableToggleIcon} aria-hidden>
                      {tableExpanded ? "▾" : "▸"}
                    </span>
                    <span>
                      {isAverageView
                        ? "League min / max / average table"
                        : "Season stats table"}
                      <span className={styles.tableToggleMeta}>
                        {isAverageView
                          ? `${profile.aggregates?.length ?? 0} rows`
                          : `${profile.stats.length} rows`}
                      </span>
                    </span>
                    <span className={styles.tableToggleAction}>
                      {tableExpanded ? "Hide" : "Show"}
                    </span>
                  </button>

                  {tableExpanded ? (
                    <div className={styles.tableWrap}>
                      {isAverageView ? (
                        <table className={styles.table}>
                          <thead>
                            <tr>
                              <th>Source</th>
                              <th>Category</th>
                              <th>Stat</th>
                              <th>Abbr</th>
                              <th>Average</th>
                              <th>Min</th>
                              <th>Min Team</th>
                              <th>Max</th>
                              <th>Max Team</th>
                              <th>Avg / Game</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(profile.aggregates ?? []).map((stat) => (
                              <tr
                                key={`${stat.source}-${stat.category}-${stat.name}-${stat.display_name}`}
                              >
                                <td>{stat.source}</td>
                                <td>{stat.category}</td>
                                <td>{stat.display_name}</td>
                                <td>{stat.abbreviation ?? "—"}</td>
                                <td>{stat.avg_value ?? "—"}</td>
                                <td>{stat.min_value ?? "—"}</td>
                                <td>{stat.min_team_name ?? "—"}</td>
                                <td>{stat.max_value ?? "—"}</td>
                                <td>{stat.max_team_name ?? "—"}</td>
                                <td>{stat.avg_per_game ?? "—"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <table className={styles.table}>
                          <thead>
                            <tr>
                              <th>Source</th>
                              <th>Category</th>
                              <th>Stat</th>
                              <th>Abbr</th>
                              <th>Value</th>
                              <th>Display</th>
                              <th>Per Game</th>
                              <th>Rank</th>
                            </tr>
                          </thead>
                          <tbody>
                            {profile.stats.map((stat) => (
                              <tr
                                key={`${stat.source}-${stat.category}-${stat.name}-${stat.display_name}`}
                              >
                                <td>{stat.source}</td>
                                <td>{stat.category}</td>
                                <td>{stat.display_name}</td>
                                <td>{stat.abbreviation ?? "—"}</td>
                                <td>{stat.value ?? "—"}</td>
                                <td>{stat.display_value ?? "—"}</td>
                                <td>{stat.per_game_value ?? "—"}</td>
                                <td>
                                  {stat.rank_display_value ?? stat.rank ?? "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  ) : (
                    <p className={styles.tableCollapsedHint}>
                      Table hidden. Click above to expand.
                    </p>
                  )}
                </div>
              </>
            ) : null}

            {!loading &&
            profile &&
            ((isAverageView && (profile.aggregates?.length ?? 0) === 0) ||
              (!isAverageView && profile.stats.length === 0)) ? (
              <p className={styles.muted}>
                Snapshot is empty. Run{" "}
                <code>python -m app.cli ingest</code> on the backend to fetch
                Premier League statistics, ranks, and league averages.
              </p>
            ) : null}
          </section>
        ) : null}
      </main>
    </div>
  );
}
