"use client";

import { useEffect, useRef, useState } from "react";
import { BodyMap } from "./BodyMap";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { PageMeaning } from "./PageMeaning";
import { RequireUser } from "./RequireUser";
import { ExerciseArt } from "./StretchArt";
import { ApiError, api, isSignedOut } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EXERCISE_AREAS, STRETCH_DISCLAIMER, SHARP_MESSAGE, regionById, type Exercise, type StretchType } from "@/lib/stretch-content";
import { filterExercises, prescribe, spotState, weekLabel, weekProgress, type SoreSpot, type StretchSession } from "@/lib/stretch";
import type { StretchState } from "@/lib/types";

type Mode = "loading" | "ready" | "error";

const WHEN: Record<string, string> = {
  "pre-run": "Before the run",
  "post-run": "After the run",
  "long-recovery": "After the long run",
  yoga: "On this day",
  hips: "On this day",
  primer: "Before the race",
};

function typeLabel(type: StretchType): string {
  return type === "D" ? "Dynamic" : "Static";
}

function ExerciseBlock({ exercise }: { exercise: Exercise }) {
  return (
    <article className="rio-stretch-card">
      <ExerciseArt id={exercise.id} title={exercise.name} />
      <div>
        <h3>{exercise.name}</h3>
        <p className="rio-stretch-meta">
          {exercise.area} · {typeLabel(exercise.type)} · {exercise.dose}
        </p>
        <p>{exercise.howTo}</p>
      </div>
    </article>
  );
}

export function StretchView() {
  return (
    <RequireUser>
      <StretchBody />
    </RequireUser>
  );
}

function StretchBody() {
  const { athlete, status } = useAuth();
  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  const [mode, setMode] = useState<Mode>("loading");
  const [problem, setProblem] = useState("");
  const [state, setState] = useState<StretchState | null>(null);
  const [session, setSession] = useState<StretchSession | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [area, setArea] = useState("All");
  const [kind, setKind] = useState<StretchType | "All">("All");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    let live = true;
    Promise.all([api.stretch(), api.currentSeason()])
      .then(([stretch, season]) => {
        if (!live) return;
        const sessions = season?.plan?.sessions;
        const match = Array.isArray(sessions) ? sessions.find((row) => row.date === stretch.today) : undefined;
        setState(stretch);
        setSession(match ?? null);
        setProblem("");
        setMode("ready");
      })
      .catch((caught) => {
        if (!live) return;
        if (isSignedOut(caught) && statusRef.current !== "in") return;
        setProblem(caught instanceof ApiError ? caught.message : "Stretching could not be loaded.");
        setMode("error");
      });
    return () => {
      live = false;
    };
  }, []);

  async function run(key: string, work: () => Promise<StretchState>) {
    setBusy(key);
    setProblem("");
    try {
      const next = await work();
      setState(next);
    } catch (caught) {
      if (isSignedOut(caught) && statusRef.current !== "in") return;
      setProblem(caught instanceof ApiError ? caught.message : "That could not be saved.");
    } finally {
      setBusy("");
    }
  }

  const compact = athlete?.prefs.compact === true;
  const today = state?.today || "";
  const spots: SoreSpot[] = state?.spots ?? [];
  const prescription = today
    ? prescribe({ today, session, spots, completions: state?.completions ?? [] })
    : null;
  const progress = today ? weekProgress(state?.completions ?? [], today) : null;
  const library = filterExercises(area, kind);
  const pickedRegion = picked ? regionById(picked) : undefined;
  const pickedSpot = picked ? spots.find((spot) => spot.region === picked && !spot.cleared) : undefined;

  return (
    <div className={compact ? "page-stretch is-compact" : "page-stretch"}>
      <Nav active="Stretching" />
      <main>
        <header className="rio-hero">
          <h1>Stretching</h1>
          <p className="rio-range">
            A short routine for today, taken from the plan. Dynamic moves come before a run. Static holds come after, or on an easy day.
          </p>
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {problem ? <p className="rio-error">{problem}</p> : null}
        {mode === "ready" && prescription && progress ? (
          <>
            <section className="rio-stretch-today" data-testid="stretch-prescription" aria-labelledby="stretch-today">
              <p className="rio-index">Today · {prescription.kindLabel}</p>
              <h2 id="stretch-today">Today&apos;s prescription</h2>
              <p className="rio-stretch-week" data-testid="stretch-week">
                {weekLabel(progress)}
              </p>
              {prescription.checkIns.map((region) => (
                <div key={region.id} className="rio-stretch-check">
                  <p>
                    <strong>{region.label}.</strong> Still bothering you?
                  </p>
                  <div className="rio-stretch-actions">
                    <button type="button" className="rio-primary" disabled={busy !== ""} onClick={() => void run(`yes-${region.id}`, () => api.stretchCheckIn(region.id, true))}>
                      Yes
                    </button>
                    <button type="button" className="rio-secondary" disabled={busy !== ""} onClick={() => void run(`no-${region.id}`, () => api.stretchCheckIn(region.id, false))}>
                      No
                    </button>
                  </div>
                </div>
              ))}
              {spots
                .filter((spot) => spotState(spot, today) === "active")
                .map((spot) => {
                  const region = regionById(spot.region);
                  if (!region) return null;
                  return (
                    <p key={spot.region} className="rio-stretch-active">
                      {region.label} · {spot.severity === "mild" ? "Mild" : "Moderate"}
                      <button type="button" disabled={busy !== ""} onClick={() => void run(`clear-${spot.region}`, () => api.stretchClear(spot.region))}>
                        Clear
                      </button>
                    </p>
                  );
                })}
              {prescription.sharp.map((region) => (
                <div key={region.id} className="rio-stretch-sharp" data-testid="sharp-message">
                  <p>
                    <strong>{region.label}.</strong> {SHARP_MESSAGE}
                  </p>
                  <button type="button" className="rio-secondary" disabled={busy !== ""} onClick={() => void run(`clear-${region.id}`, () => api.stretchClear(region.id))}>
                    Clear
                  </button>
                </div>
              ))}
              {prescription.extras.length > 0 ? (
                <div data-testid="stretch-extras">
                  <h3>Extra for sore spots</h3>
                  {prescription.extras.map((exercise) => (
                    <ExerciseBlock key={exercise.id} exercise={exercise} />
                  ))}
                </div>
              ) : null}
              {prescription.routines.map((item) => (
                <section key={item.routine.id} className="rio-stretch-routine" aria-labelledby={`routine-${item.routine.id}`}>
                  <div className="rio-stretch-routine-head">
                    <div>
                      <p className="rio-stretch-meta">{WHEN[item.routine.id] || "Today"}</p>
                      <h3 id={`routine-${item.routine.id}`}>
                        {item.routine.name}
                        <span> · about {item.routine.minutes} min</span>
                      </h3>
                    </div>
                    <button
                      type="button"
                      className={item.done ? "rio-primary" : "rio-secondary"}
                      aria-pressed={item.done}
                      aria-label={item.done ? `${item.routine.name} done` : `Mark ${item.routine.name} done`}
                      disabled={busy !== ""}
                      onClick={() => void run(item.routine.id, () => api.stretchComplete(item.routine.id))}
                    >
                      {item.done ? "Done today" : "Done"}
                    </button>
                  </div>
                  {item.exercises.map((exercise) => (
                    <ExerciseBlock key={`${item.routine.id}-${exercise.id}`} exercise={exercise} />
                  ))}
                </section>
              ))}
            </section>
            <section className="rio-stretch-map" aria-labelledby="stretch-map">
              <h2 id="stretch-map">Sore spots</h2>
              <p className="rio-note">
                Tap an area. Mild or moderate adds two or three stretches from that area for 7 days, at the top of each day. You can clear a spot any time.
              </p>
              <BodyMap selected={picked} onPick={setPicked} />
              {pickedRegion ? (
                <div className="rio-severity" role="group" aria-label={`How ${pickedRegion.label} feels`}>
                  <h3>{pickedRegion.label}</h3>
                  <p>How does it feel?</p>
                  <div className="rio-stretch-actions">
                    <button type="button" className="rio-secondary" aria-pressed={pickedSpot?.severity === "mild"} disabled={busy !== ""} onClick={() => void run("mild", () => api.stretchSpot(pickedRegion.id, "mild"))}>
                      Mild
                    </button>
                    <button type="button" className="rio-secondary" aria-pressed={pickedSpot?.severity === "moderate"} disabled={busy !== ""} onClick={() => void run("moderate", () => api.stretchSpot(pickedRegion.id, "moderate"))}>
                      Moderate
                    </button>
                    <button type="button" className="rio-secondary" aria-pressed={pickedSpot?.severity === "sharp"} disabled={busy !== ""} onClick={() => void run("sharp", () => api.stretchSpot(pickedRegion.id, "sharp"))}>
                      Sharp pain / getting worse
                    </button>
                    {pickedSpot ? (
                      <button type="button" className="rio-text-link" disabled={busy !== ""} onClick={() => void run("clear-picked", () => api.stretchClear(pickedRegion.id))}>
                        Clear
                      </button>
                    ) : null}
                  </div>
                </div>
              ) : null}
              <p className="rio-disclaimer">{STRETCH_DISCLAIMER}</p>
            </section>
            <section className="rio-stretch-library" data-testid="stretch-library" aria-labelledby="stretch-library-title">
              <h2 id="stretch-library-title">Exercise library</h2>
              <div className="rio-stretch-filters" role="group" aria-label="Body area">
                <button type="button" aria-pressed={area === "All"} onClick={() => setArea("All")}>
                  All areas
                </button>
                {EXERCISE_AREAS.map((name) => (
                  <button key={name} type="button" aria-pressed={area === name} onClick={() => setArea(name)}>
                    {name}
                  </button>
                ))}
              </div>
              <div className="rio-stretch-filters" role="group" aria-label="Dynamic or static">
                <button type="button" aria-pressed={kind === "All"} onClick={() => setKind("All")}>
                  All types
                </button>
                <button type="button" aria-pressed={kind === "D"} onClick={() => setKind("D")}>
                  Dynamic
                </button>
                <button type="button" aria-pressed={kind === "S"} onClick={() => setKind("S")}>
                  Static
                </button>
              </div>
              <p className="rio-lib-count">
                {library.length} {library.length === 1 ? "exercise" : "exercises"}
              </p>
              {library.map((exercise) => (
                <ExerciseBlock key={exercise.id} exercise={exercise} />
              ))}
            </section>
          </>
        ) : null}
        <PageMeaning page="stretching" />
        <Footer />
      </main>
    </div>
  );
}
