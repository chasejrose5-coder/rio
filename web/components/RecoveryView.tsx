"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Disclosure } from "./Disclosure";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { PageMeaning } from "./PageMeaning";
import { RequireUser } from "./RequireUser";
import { ApiError, api, isSignedOut, previewing } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ErrorText, LoadError } from "./ErrorText";
import {
  AREAS,
  BONE_MESSAGE,
  EXERCISES,
  GROUPS,
  LEVELS,
  exercisesFor,
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

function withArea(state: InjuryState, areaId: string): InjuryState {
  if (state.areas.some((area) => area.area_id === areaId)) return state;
  return {
    ...state,
    areas: [
      ...state.areas,
      { area_id: areaId, anchor_on: state.today, level: 0, level_now: 0, level_name: "easy" },
    ],
  };
}

function withoutArea(state: InjuryState, areaId: string): InjuryState {
  return { ...state, areas: state.areas.filter((area) => area.area_id !== areaId) };
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
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<InjuryState | null>(null);
  const [group, setGroup] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const [libraryGroup, setLibraryGroup] = useState("All");
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
  }, [attempt]);

  async function save(area: InjuryArea, next: "select" | "clear" | "back") {
    if (!state || busyRef.current || previewing()) return;
    const snapshot = state;
    busyRef.current = area.id;
    setProblem("");
    if (next === "select") setState(withArea(state, area.id));
    if (next === "clear") setState(withoutArea(state, area.id));
    try {
      const body =
        next === "select"
          ? await api.injurySelect(area.id)
          : next === "clear"
            ? await api.injuryClear(area.id)
            : await api.injuryStepBack(area.id);
      setState(body);
      setMode("ready");
    } catch (caught) {
      if (isSignedOut(caught) && statusRef.current !== "in") return;
      if (next !== "back") setState(snapshot);
      setProblem(caught instanceof ApiError ? caught.message : "That could not be saved.");
    } finally {
      busyRef.current = "";
    }
  }

  const compact = athlete?.prefs.compact === true;
  const issues = AREAS.filter((area) => area.group === group);
  const shown = EXERCISES.filter((exercise) => libraryGroup === "All" || AREAS.find((area) => area.id === exercise.areaId)?.group === libraryGroup);

  return (
    <div className={compact ? "page-recovery is-compact" : "page-recovery"}>
      <Nav active="Recovery" />
      <main>
        <header className="rio-hero">
          <h1>Recovery</h1>
          <p className="rio-range">Pick an area, then the issue. The guidance opens here.</p>
        </header>
        <section className="rio-recover-ask" aria-labelledby="recover-ask">
          <h2 id="recover-ask">What&apos;s bothering you?</h2>
          <div className="rio-area-picks" role="group" aria-label="Body area">
            {GROUPS.map((name) => (
              <button
                key={name}
                type="button"
                className={group === name ? "is-on" : undefined}
                aria-pressed={group === name}
                onClick={() => {
                  setGroup(name);
                  setOpenId(null);
                }}
              >
                {name}
              </button>
            ))}
          </div>
          {group ? (
            <div className="rio-issue-list">
              {issues.map((area) => (
                <Issue
                  key={area.id}
                  area={area}
                  open={openId === area.id}
                  state={state}
                  onOpen={() => setOpenId((current) => (current === area.id ? null : area.id))}
                  onSave={(next) => void save(area, next)}
                />
              ))}
            </div>
          ) : (
            <p className="rio-note">Choose an area.</p>
          )}
        </section>
        <Disclosure title="Details">
          <div className="rio-recover-intro">
            <p>
              Everyone gets a short general set two or three days a week. Mark an area as injured last year or rebuilding and its
              exercises show up three days a week, starting easy and moving to medium, then hard, every two weeks.
            </p>
            <p>Race day and the day before stay clear. The exercises are general guidance for any runner.</p>
          </div>
        </Disclosure>
        <Disclosure title="Every exercise">
          <section className="rio-recover-library">
            <div className="rio-area-picks" role="group" aria-label="Body region">
              <button type="button" className={libraryGroup === "All" ? "is-on" : undefined} aria-pressed={libraryGroup === "All"} onClick={() => setLibraryGroup("All")}>
                All
              </button>
              {GROUPS.map((name) => (
                <button
                  key={name}
                  type="button"
                  className={libraryGroup === name ? "is-on" : undefined}
                  aria-pressed={libraryGroup === name}
                  onClick={() => setLibraryGroup(name)}
                >
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
        </Disclosure>
        {mode === "loading" ? <p className="rio-wait">Loading saved areas</p> : null}
        {mode === "error" ? <LoadError message={problem} onRetry={() => setAttempt((value) => value + 1)} /> : null}
        {problem && mode !== "error" ? <ErrorText>{problem}</ErrorText> : null}
        <PageMeaning page="recovery" />
        <Footer />
      </main>
    </div>
  );
}

function Issue({
  area,
  open,
  state,
  onOpen,
  onSave,
}: {
  area: InjuryArea;
  open: boolean;
  state: InjuryState | null;
  onOpen: () => void;
  onSave: (next: "select" | "clear" | "back") => void;
}) {
  const panelId = useId();
  const row = state?.areas.find((item) => item.area_id === area.id);
  const level = row?.level_name ?? "easy";
  const exercises = area.bone ? [] : exercisesFor(area.id, level);
  return (
    <div className={open ? "rio-issue-wrap is-open" : "rio-issue-wrap"}>
      <button type="button" className={open ? "rio-issue is-open" : "rio-issue"} aria-expanded={open} aria-controls={panelId} onClick={onOpen}>
        <span className="rio-issue-label">
          {area.label}
          {row ? <span className="rio-issue-tag">Rebuilding</span> : null}
        </span>
        <span className="rio-issue-blurb">{area.blurb}</span>
      </button>
      {open ? (
        <div id={panelId} className="rio-issue-panel">
          {area.bone ? <p className="rio-medical">{BONE_MESSAGE}</p> : null}
          {exercises.map((item) => (
            <article key={item.exercise.id} className="rio-stretch-card">
              <h3>{item.exercise.name}</h3>
              <p className="rio-stretch-meta">
                {levelLabel(level)} · {item.dose}
              </p>
              <p>{item.exercise.howTo}</p>
              <Disclosure title="Details">
                <ul className="rio-level-list">
                  {LEVELS.map((name) => (
                    <li key={name}>
                      <span>{levelLabel(name)}</span>
                      <span>{item.exercise.doses[name]}</span>
                    </li>
                  ))}
                </ul>
              </Disclosure>
            </article>
          ))}
          <div className="rio-recover-level">
            {row && !area.bone ? (
              <span>
                {area.label} is {levelLabel(level)}. It moves up every two weeks.
              </span>
            ) : (
              <span>{row ? `${area.label} is marked for rebuilding.` : "Not marked for rebuilding."}</span>
            )}
            <button type="button" className={row ? "rio-secondary" : "rio-primary"} disabled={!state || previewing()} onClick={() => onSave(row ? "clear" : "select")}>
              {row ? "Stop rebuilding" : "Rebuild this"}
            </button>
            {row && !area.bone && row.level_now > 0 ? (
              <button type="button" className="rio-secondary" disabled={!state || previewing()} onClick={() => onSave("back")}>
                It hurt, step back a level
              </button>
            ) : null}
            {row && !area.bone && row.level_now === 0 ? <span className="rio-note">Already at easy.</span> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
