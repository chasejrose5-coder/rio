"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { Footer } from "./Footer";
import { PageMeaning } from "./PageMeaning";
import { Nav } from "./Nav";
import { SkeletonBlocks } from "./PageSkeleton";
import { RequireUser } from "./RequireUser";
import { ApiError, api, isSignedOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { capacityClass, countLabel } from "@/lib/library";
import type { LibraryResponse } from "@/lib/types";
import { LoadError } from "./ErrorText";

const FAMILY_HELP = "The quality that workout builds, such as speed or endurance.";
const PHASE_HELP = "A phase is a training block. The season moves through eight of them.";
const PHASES = [1, 2, 3, 4, 5, 6, 7, 8];

type Mode = "loading" | "ready" | "error";

export function LibraryView() {
  return (
    <RequireUser title="Library" pageClass="page-library">
      <LibraryBody />
    </RequireUser>
  );
}

function LibraryBody() {
  const { athlete, status } = useAuth();
  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  const [mode, setMode] = useState<Mode>("loading");
  const [data, setData] = useState<LibraryResponse | null>(null);
  const [problem, setProblem] = useState("");
  const [attempt, setAttempt] = useState(0);
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
        if (isSignedOut(caught) && statusRef.current !== "in") return;
        setData(null);
        setProblem(caught instanceof ApiError ? caught.message : "The workout library could not be loaded. Try again.");
        setMode("error");
      });
    return () => {
      live = false;
    };
  }, [debounced, family, phase, attempt]);

  const showIds = athlete?.prefs.show_ids === true;
  const compact = athlete?.prefs.compact === true;
  const families = data?.families ?? [];
  const stickRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    const bar = stickRef.current;
    const sentinel = bar?.previousElementSibling;
    if (!bar || !sentinel) return;
    const observer = new IntersectionObserver(([entry]) => {
      bar.classList.toggle("is-stuck", !entry.isIntersecting);
    });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [mode]);

  return (
    <div className={compact ? "page-library rio-v3 is-compact" : "page-library rio-v3"}>
      <Nav active="Library" pending={status !== "in"} />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>Library</h1>
          <p className="rio-range">Every workout RIO can put in your plan.</p>
        </header>
        {mode === "loading" ? <SkeletonBlocks /> : null}
        {mode !== "loading" ? (
          <>
          <div className="rio-stick-sentinel" aria-hidden="true" />
          <form className="rio-library" ref={stickRef} onSubmit={(event) => event.preventDefault()}>
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
                  <HelpTip text={FAMILY_HELP} label="What it trains: help" />
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
                  <HelpTip text={PHASE_HELP} label="Phase: help" />
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
          </>
        ) : null}
        {mode === "error" ? <LoadError message={problem} onRetry={() => setAttempt((value) => value + 1)} /> : null}
        {mode === "ready" && data ? (
          <>
            <p className="rio-week-meta rio-lib-count" role="status">{countLabel(data.count)}</p>
            {data.count === 0 ? (
              <p className="rio-empty">No workouts.</p>
            ) : (
              <div className="rio-lib">
                {data.workouts.map((row, index) => {
                  const previous = index > 0 ? data.workouts[index - 1]?.capacity : "";
                  return (
                  <Fragment key={row.id}>
                  {row.capacity && row.capacity !== previous ? <h2 className="rio-lib-group">{row.capacity}</h2> : null}
                  <div className="rio-lib-row">
                    <div className="rio-lib-main">
                      <div className="rio-lib-name">{row.description || "—"}</div>
                      {showIds ? <div className="rio-lib-id">{row.id}</div> : null}
                    </div>
                    <div className={capacityClass(row.family)}>{row.capacity || "—"}</div>
                  </div>
                  </Fragment>
                  );
                })}
              </div>
            )}
          </>
        ) : null}
        <PageMeaning page="library" />
        <Footer />
      </main>
    </div>
  );
}

function HelpTip({ text, label }: { text: string; label: string }) {
  const [open, setOpen] = useState(false);
  const tipId = `help-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <span className={open ? "rio-help is-open" : "rio-help"}>
      <button
        type="button"
        className="rio-help-btn"
        aria-label={label}
        aria-expanded={open}
        aria-describedby={open ? tipId : undefined}
        onClick={() => setOpen((value) => !value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
      >
        ?
      </button>
      <span className="rio-help-tip" id={tipId} role="tooltip">
        {text}
      </span>
    </span>
  );
}
