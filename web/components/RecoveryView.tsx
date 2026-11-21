"use client";

import { useEffect, useRef, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { PageMeaning } from "./PageMeaning";
import { RequireUser } from "./RequireUser";
import { ApiError, api, isSignedOut, previewing } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  AREAS,
  BONE_MESSAGE,
  EXERCISES,
  GROUPS,
  INJURY_DISCLAIMER,
  LEVELS,
  type InjuryArea,
  type LevelName,
} from "@/lib/injury-content";
import type { InjuryState } from "@/lib/types";

type Mode = "loading" | "ready" | "error";

function levelLabel(level: LevelName): string {
  if (level === "easy") return "Easy";
  if (level === "medium") return "Medium";
  return "Hard";
}

export function RecoveryView() {
  return (
    <RequireUser title="Recovery" pageClass="page-recovery">
      <RecoveryBody />
    </RequireUser>
  );
}

function RecoveryBody() {
  const { athlete, status } = useAuth();
  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  const [mode, setMode] = useState<Mode>("loading");
  const [problem, setProblem] = useState("");
  const [state, setState] = useState<InjuryState | null>(null);
  const [group, setGroup] = useState("All");
  const [busy, setBusy] = useState("");
  const busyRef = useRef("");

  useEffect(() => {
    let live = true;
    api
      .injury()
      .then((body) => {
        if (!live) return;
        setState(body);
        setMode("ready");
      })
      .catch((caught: unknown) => {
        if (!live) return;
        if (isSignedOut(caught) && statusRef.current !== "in") return;
        setProblem(caught instanceof ApiError ? caught.message : "Recovery could not be loaded.");
        setMode("error");
      });
    return () => {
      live = false;
    };
  }, []);

  async function run(key: string, work: () => Promise<InjuryState>) {
    if (busyRef.current || previewing()) return;
    busyRef.current = key;
    setProblem("");
    setBusy(key);
    try {
      setState(await work());
    } catch (caught) {
      if (isSignedOut(caught) && statusRef.current !== "in") return;
      setProblem(caught instanceof ApiError ? caught.message : "That could not be saved.");
    } finally {
      busyRef.current = "";
      setBusy("");
    }
  }

  const compact = athlete?.prefs.compact === true;
  const selected = new Map((state?.areas ?? []).map((area) => [area.area_id, area]));
  const shown = EXERCISES.filter((exercise) => group === "All" || AREAS.find((area) => area.id === exercise.areaId)?.group === group);

  return (
    <div className={compact ? "page-recovery is-compact" : "page-recovery"}>
      <Nav active="Recovery" />
      <main>
        <header className="rio-hero">
          <h1>Recovery</h1>
          <p className="rio-range">{INJURY_DISCLAIMER}</p>
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode === "error" ? <p className="rio-error">{problem}</p> : null}
        {mode === "ready" ? (
          <>
            <section className="rio-recover-intro">
              <p>
                Everyone gets a short general set two or three days a week. Mark an area as injured last year or rebuilding and its
                exercises show up three days a week, starting easy and moving to medium, then hard, every two weeks.
              </p>
              <p>Race day and the day before stay clear. The exercises are general guidance for any runner.</p>
            </section>
            {GROUPS.map((name) => (
              <section key={name} className="rio-recover-group">
                <h2>{name}</h2>
                <div className="rio-area-picks">
                  {AREAS.filter((area) => area.group === name).map((area) => {
                    const on = selected.has(area.id);
                    return (
                      <button
                        key={area.id}
                        type="button"
                        className={on ? "is-on" : undefined}
                        aria-pressed={on}
                        disabled={busy === area.id}
                        onClick={() =>
                          void run(area.id, () => (on ? api.injuryClear(area.id) : api.injurySelect(area.id)))
                        }
                      >
                        {area.label}
                      </button>
                    );
                  })}
                </div>
                {AREAS.filter((area) => area.group === name && selected.has(area.id)).map((area) => (
                  <Selected key={area.id} area={area} state={state} busy={busy} onStep={() => void run(`${area.id}-back`, () => api.injuryStepBack(area.id))} />
                ))}
              </section>
            ))}
            <section className="rio-recover-library">
              <h2>Every exercise</h2>
              <div className="rio-area-picks" role="group" aria-label="Body region">
                <button type="button" className={group === "All" ? "is-on" : undefined} onClick={() => setGroup("All")}>
                  All
                </button>
                {GROUPS.map((name) => (
                  <button key={name} type="button" className={group === name ? "is-on" : undefined} onClick={() => setGroup(name)}>
                    {name}
                  </button>
                ))}
              </div>
              {shown.map((exercise) => {
                const area = AREAS.find((item) => item.id === exercise.areaId);
                return (
                  <article key={exercise.id} className="rio-stretch-card">
                    <h3>{exercise.name}</h3>
                    <p className="rio-stretch-meta">{area?.label}</p>
                    <ul className="rio-level-list">
                      {LEVELS.map((level) => (
                        <li key={level}>
                          <span>{levelLabel(level)}</span>
                          <span>{exercise.doses[level]}</span>
                        </li>
                      ))}
                    </ul>
                    <p>{exercise.howTo}</p>
                  </article>
                );
              })}
            </section>
            {problem ? <p className="rio-error">{problem}</p> : null}
            <p className="rio-medical">{INJURY_DISCLAIMER}</p>
          </>
        ) : null}
        <PageMeaning page="recovery" />
        <Footer />
      </main>
    </div>
  );
}

function Selected({
  area,
  state,
  busy,
  onStep,
}: {
  area: InjuryArea;
  state: InjuryState | null;
  busy: string;
  onStep: () => void;
}) {
  const row = state?.areas.find((item) => item.area_id === area.id);
  if (!row) return null;
  if (area.bone) {
    return <p className="rio-medical">{BONE_MESSAGE}</p>;
  }
  const name = row.level_name;
  return (
    <p className="rio-recover-level">
      <span>
        {area.label} is {levelLabel(name)}. It moves up every two weeks.
      </span>
      {row.level_now > 0 ? (
        <button type="button" className="rio-secondary" disabled={busy === `${area.id}-back`} onClick={onStep}>
          It hurt, step back a level
        </button>
      ) : (
        <span className="rio-note">Already at easy.</span>
      )}
    </p>
  );
}
