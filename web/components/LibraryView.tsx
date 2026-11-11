"use client";

import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { capacityClass, countLabel } from "@/lib/library";
import type { LibraryResponse } from "@/lib/types";

const FAMILY_HELP = "The quality that workout builds, such as speed or endurance.";
const PHASE_HELP = "A phase is a training block. The season moves through eight of them.";
const PHASES = [1, 2, 3, 4, 5, 6, 7, 8];

type Mode = "loading" | "ready" | "error";

export function LibraryView() {
  return (
    <RequireUser>
      <LibraryBody />
    </RequireUser>
  );
}

function LibraryBody() {
  const { athlete } = useAuth();
  const [mode, setMode] = useState<Mode>("loading");
  const [data, setData] = useState<LibraryResponse | null>(null);
  const [problem, setProblem] = useState("");
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [family, setFamily] = useState("All");
  const [phase, setPhase] = useState("All");
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query), 200);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "library";
    window.sessionStorage.setItem(key, "library");
    if (first) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setArm(true);
    }
  }, []);

  useEffect(() => {
    if (!arm || mode !== "ready") return;
    // The rows rise once, after the menu is on screen. A filter does not replay it.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRise(true);
    const timer = window.setTimeout(() => setRise(false), 280);
    return () => window.clearTimeout(timer);
  }, [arm, mode]);

  useEffect(() => {
    let live = true;
    const chosenFamily = family === "All" ? "" : family;
    const chosenPhase = phase === "All" ? undefined : Number(phase);
    api
      .library({ q: debounced, family: chosenFamily, phase: chosenPhase })
      .then((body) => {
        if (!live) return;
        setData(body);
        setProblem("");
        setMode("ready");
      })
      .catch((caught) => {
        if (!live) return;
        setData(null);
        setProblem(caught instanceof ApiError ? caught.message : "The menu could not be loaded.");
        setMode("error");
      });
    return () => {
      live = false;
    };
  }, [debounced, family, phase]);

  const showIds = athlete?.prefs.show_ids === true;
  const compact = athlete?.prefs.compact === true;
  const families = data?.families ?? [];

  return (
    <div className={compact ? "page-library is-compact" : "page-library"}>
      <Nav active="Library" />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>Library</h1>
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode !== "loading" ? (
          <form className="rio-library" onSubmit={(event) => event.preventDefault()}>
            <label className="rio-library-search" htmlFor="library-search">
              Search
              <input
                id="library-search"
                value={query}
                placeholder="Search workouts"
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <div className="rio-library-filters">
              <label htmlFor="library-capacity">
                <span className="rio-filter-label">
                  What it trains
                  <HelpTip text={FAMILY_HELP} />
                </span>
                <select id="library-capacity" value={family} onChange={(event) => setFamily(event.target.value)}>
                  <option value="All">All</option>
                  {families.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </label>
              <label htmlFor="library-phase">
                <span className="rio-filter-label">
                  Phase
                  <HelpTip text={PHASE_HELP} />
                </span>
                <select id="library-phase" value={phase} onChange={(event) => setPhase(event.target.value)}>
                  <option value="All">All</option>
                  {PHASES.map((item) => (
                    <option key={item} value={String(item)}>
                      Phase {item}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </form>
        ) : null}
        {mode === "error" ? <p className="rio-error">{problem}</p> : null}
        {mode === "ready" && data ? (
          <>
            <p className="rio-week-meta rio-lib-count">{countLabel(data.count)}</p>
            {data.count === 0 ? (
              <p className="rio-empty">No workouts.</p>
            ) : (
              <div className="rio-lib">
                {data.workouts.map((row) => (
                  <div className="rio-lib-row" key={row.id}>
                    <div className="rio-lib-main">
                      <div className="rio-lib-name">{row.description || "—"}</div>
                      {showIds ? <div className="rio-lib-id">{row.id}</div> : null}
                    </div>
                    <div className={capacityClass(row.family)}>{row.capacity || "—"}</div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : null}
        <Footer />
      </main>
    </div>
  );
}

function HelpTip({ text }: { text: string }) {
  return (
    <span className="rio-help">
      <button type="button" className="rio-help-btn" aria-label="Help">
        ?
      </button>
      <span className="rio-help-tip" role="tooltip">
        {text}
      </span>
    </span>
  );
}
