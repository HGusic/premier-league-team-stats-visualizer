"use client";

import { useEffect, useMemo, useRef } from "react";
import type { Team } from "./types";
import styles from "./page.module.css";

const COPIES = 3;

type TeamBarProps = {
  teams: Team[];
  selectedTeamId: string;
  isAverageView: boolean;
  onSelectAverage: () => void;
  onSelectTeam: (espnId: string) => void;
};

export function TeamBar({
  teams,
  selectedTeamId,
  isAverageView,
  onSelectAverage,
  onSelectTeam,
}: TeamBarProps) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const adjustingRef = useRef(false);

  const loopedTeams = useMemo(
    () =>
      Array.from({ length: COPIES }, (_, copyIndex) =>
        teams.map((team) => ({ team, copyIndex })),
      ).flat(),
    [teams],
  );

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || teams.length === 0) return;

    const centerOnMiddleCopy = () => {
      const segment = el.scrollWidth / COPIES;
      if (segment > 0) {
        el.scrollLeft = segment;
      }
    };

    centerOnMiddleCopy();
    const frame = window.requestAnimationFrame(centerOnMiddleCopy);
    return () => window.cancelAnimationFrame(frame);
  }, [teams]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;

    const onWheel = (event: WheelEvent) => {
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
      event.preventDefault();
      el.scrollLeft += event.deltaY;
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const handleScroll = () => {
    const el = scrollerRef.current;
    if (!el || adjustingRef.current || teams.length === 0) return;

    const segment = el.scrollWidth / COPIES;
    if (segment <= 0) return;

    if (el.scrollLeft < segment * 0.35) {
      adjustingRef.current = true;
      el.scrollLeft += segment;
      adjustingRef.current = false;
    } else if (el.scrollLeft > segment * 1.65) {
      adjustingRef.current = true;
      el.scrollLeft -= segment;
      adjustingRef.current = false;
    }
  };

  return (
    <header className={styles.teamBar}>
      <button
        type="button"
        className={`${styles.teamChip} ${styles.averageChip} ${isAverageView ? styles.teamChipActive : ""}`}
        onClick={onSelectAverage}
      >
        <span>Average</span>
      </button>

      <div
        ref={scrollerRef}
        className={styles.teamScroller}
        onScroll={handleScroll}
      >
        {teams.length === 0 ? (
          <span className={styles.muted}>Loading teams…</span>
        ) : (
          <div className={styles.teamTrack}>
            {loopedTeams.map(({ team, copyIndex }) => {
              const active = !isAverageView && team.espn_id === selectedTeamId;
              return (
                <button
                  key={`${copyIndex}-${team.espn_id}`}
                  type="button"
                  className={`${styles.teamChip} ${active ? styles.teamChipActive : ""}`}
                  onClick={() => onSelectTeam(team.espn_id)}
                >
                  {team.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={team.logo_url}
                      alt=""
                      className={styles.teamLogo}
                    />
                  ) : null}
                  <span>{team.name}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </header>
  );
}
