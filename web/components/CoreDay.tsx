"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclosure } from "./Disclosure";
import { ApiError, api, previewing } from "@/lib/api";
import {
  CATEGORIES,
  CATEGORY_LABEL,
  CORE_DISCLAIMER,
  CORE_EXERCISES,
  circuitFor,
} from "@/lib/core-content";
import type { StretchSession } from "@/lib/stretch-content";
import type { CoreState } from "@/lib/types";
import { LoadError } from "./ErrorText";

export function CoreDay({ date, session, bare = false }: { date: string; session?: StretchSession; bare?: boolean }) {
  const [state, setState] = useState<CoreState | null>(null);
  const [sessions, setSessions] = useState<StretchSession[]>([]);
  const [offline, setOffline] = useState(false);
  const [problem, setProblem] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    Promise.all([
      api.core().catch((caught: unknown) => {
        if (caught instanceof ApiError && (caught.status === 404 || caught.status === 503)) return null;
        throw caught;
      }),
      api.currentSeason().catch(() => null),
    ])
      .then(([core, season]) => {
        if (!live) return;
        setState(core);
        setOffline(core == null);
        const planSessions = season?.plan?.sessions;
        setSessions(Array.isArray(planSessions) ? planSessions : []);
      })
      .catch((caught: unknown) => {
        if (!live) return;
        setProblem(caught instanceof ApiError ? caught.message : "Core could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [date, attempt]);

  const known = session?.date === date ? [session, ...sessions.filter((item) => item.date !== date)] : sessions;
  const circuit = date ? circuitFor(date, known) : null;
  const done = (state?.completions ?? []).some((row) => row.date.slice(0, 10) === date);
  const canSave = state != null && !previewing() && state.today === date && circuit != null;

  return (
    <section className="rio-core-block" aria-label="Core circuit">
      {bare ? null : <p className="rio-mark-label">Core circuit</p>}
      <p className="rio-medical">{CORE_DISCLAIMER}</p>
      {circuit == null ? (
        <p className="rio-note">None today. Race day and the day before stay clear.</p>
      ) : (
        <>
          <h3>
            {circuit.label}
            <span> · {circuit.kind === "quality" || circuit.kind === "long" ? "Hard day" : "Easy day"}</span>
          </h3>
          <ul className="rio-prep-list">
            {circuit.exercises.map((exercise, index) => (
              <li key={`${exercise.id}-${index}`}>
                <strong>
                  {exercise.name} · {exercise.dose}
                </strong>
              </li>
            ))}
          </ul>
          {circuit.exercises.map((exercise, index) => (
            <p key={`${exercise.id}-how-${index}`}>
              <strong>
                {exercise.name}. {CATEGORY_LABEL[exercise.category]}.
              </strong>{" "}
              {exercise.howTo}
            </p>
          ))}
          {canSave ? (
            <button
              type="button"
              className={done ? "rio-secondary" : "rio-primary"}
              disabled={busy}
              onClick={() => {
                setBusy(true);
                setProblem("");
                void api
                  .coreComplete(!done)
                  .then(setState)
                  .catch((caught: unknown) => {
                    setProblem(caught instanceof ApiError ? caught.message : "That could not be saved.");
                  })
                  .finally(() => setBusy(false));
              }}
            >
              {done ? "Done" : "Mark done"}
            </button>
          ) : null}
        </>
      )}
      {offline ? <p className="rio-note">Saving is unavailable until the core table is in place.</p> : null}
      {problem ? <LoadError message={problem} onRetry={() => setAttempt((value) => value + 1)} /> : null}
      <p className="rio-stretch-link">
        <Link href="/core">Browse the core library</Link>
      </p>
    </section>
  );
}

export function CoreLibrary() {
  return (
    <>
      {CATEGORIES.map((category) => (
        <Disclosure key={category} className="rio-calm-group" title={CATEGORY_LABEL[category]}>
          {CORE_EXERCISES.filter((exercise) => exercise.category === category).map((exercise) => (
            <div key={exercise.id} className="rio-calm-row">
              <h3>{exercise.name}</h3>
              <p>
                {exercise.dose}. {exercise.howTo}
              </p>
            </div>
          ))}
        </Disclosure>
      ))}
      <Disclosure className="rio-calm-group" title="How the day is chosen">
        <p>
          A hard day or a long run is about 8 minutes. An easy or rest day is 12 to 15 minutes. Race day and the day before
          are left clear. The five categories rotate so the week uses each of them, and the exercises change the next week.
        </p>
      </Disclosure>
    </>
  );
}
