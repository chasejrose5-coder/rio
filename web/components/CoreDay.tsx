"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclosure } from "./Disclosure";
import { Expander } from "./Expander";
import { ApiError, api, previewing } from "@/lib/api";
import {
  CATEGORIES,
  CATEGORY_LABEL,
  CORE_EXERCISES,
  circuitFor,
} from "@/lib/core-content";
import type { StretchSession } from "@/lib/stretch-content";
import type { CoreState } from "@/lib/types";

export function CoreDay({ date, session }: { date: string; session?: StretchSession }) {
  const [state, setState] = useState<CoreState | null>(null);
  const [sessions, setSessions] = useState<StretchSession[]>([]);
  const [offline, setOffline] = useState(false);
  const [problem, setProblem] = useState("");
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
  }, [date]);

  const known = session?.date === date ? [session, ...sessions.filter((item) => item.date !== date)] : sessions;
  const circuit = date ? circuitFor(date, known) : null;
  const done = (state?.completions ?? []).some((row) => row.date.slice(0, 10) === date);
  const canSave = state != null && !previewing() && state.today === date && circuit != null;

  return (
    <section className="rio-core-block" aria-label="Core circuit">
      <p className="rio-mark-label">Core circuit</p>
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
          <Disclosure title="Details">
            {circuit.exercises.map((exercise, index) => (
              <p key={`${exercise.id}-how-${index}`}>
                <strong>
                  {exercise.name}. {CATEGORY_LABEL[exercise.category]}.
                </strong>{" "}
                {exercise.howTo}
              </p>
            ))}
          </Disclosure>
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
      {problem ? <p className="rio-error">{problem}</p> : null}
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
        <section key={category}>
          <h2>{CATEGORY_LABEL[category]}</h2>
          {CORE_EXERCISES.filter((exercise) => exercise.category === category).map((exercise) => (
            <article key={exercise.id} className="rio-stretch-card">
              <h3>{exercise.name}</h3>
              <p className="rio-stretch-meta">{exercise.dose}</p>
              <Disclosure title="Details">
                <p>{exercise.howTo}</p>
              </Disclosure>
            </article>
          ))}
        </section>
      ))}
      <Expander title="How the day is chosen">
        <p>
          A hard day or a long run is about 8 minutes. An easy or rest day is 12 to 15 minutes. Race day and the day before
          are left clear. The five categories rotate so the week uses each of them, and the exercises change the next week.
        </p>
      </Expander>
    </>
  );
}
