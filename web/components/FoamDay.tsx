"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclosure } from "./Disclosure";
import { ApiError, api, previewing } from "@/lib/api";
import { FOAM_AREAS, FOAM_DISCLAIMER, clock, foamRoutine } from "@/lib/foam-content";
import type { StretchSession } from "@/lib/stretch-content";
import type { FoamState } from "@/lib/types";

export function FoamDay({ date, session }: { date: string; session?: StretchSession }) {
  const [state, setState] = useState<FoamState | null>(null);
  const [sessions, setSessions] = useState<StretchSession[]>([]);
  const [offline, setOffline] = useState(false);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    Promise.all([
      api.foam().catch((caught: unknown) => {
        if (caught instanceof ApiError && (caught.status === 404 || caught.status === 503)) return null;
        throw caught;
      }),
      api.currentSeason().catch(() => null),
    ])
      .then(([foam, season]) => {
        if (!live) return;
        setState(foam);
        setOffline(foam == null);
        const planSessions = season?.plan?.sessions;
        setSessions(Array.isArray(planSessions) ? planSessions : []);
      })
      .catch((caught: unknown) => {
        if (!live) return;
        setProblem(caught instanceof ApiError ? caught.message : "Foam rolling could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [date]);

  const known = session?.date === date ? [session, ...sessions.filter((item) => item.date !== date)] : sessions;
  const routine = date ? foamRoutine(date, known) : null;
  const done = (state?.completions ?? []).some((row) => row.date.slice(0, 10) === date);
  const canSave = state != null && !previewing() && state.today === date;

  return (
    <section className="rio-foam-block" aria-label="Foam rolling">
      <p className="rio-mark-label">Foam rolling</p>
      <p className="rio-medical">{FOAM_DISCLAIMER}</p>
      {routine ? (
        <>
          <h3>{routine.label}</h3>
          <ul className="rio-prep-list">
            {routine.areas.map((area) => (
              <li key={area.id}>
                <strong>
                  {area.name} · {clock(area.seconds)}
                </strong>
              </li>
            ))}
          </ul>
          <Disclosure title="Details">
            {routine.areas.map((area) => (
              <p key={`${area.id}-how`}>
                <strong>{area.name}.</strong> {area.howTo}
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
                  .foamComplete(!done)
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
      ) : null}
      {offline ? <p className="rio-note">Saving is unavailable until the foam-rolling table is in place.</p> : null}
      {problem ? <p className="rio-error">{problem}</p> : null}
      <p className="rio-stretch-link">
        <Link href="/foam">Browse foam rolling</Link>
      </p>
    </section>
  );
}

export function FoamLibrary() {
  return (
    <>
      {FOAM_AREAS.map((area) => (
        <article key={area.id} className="rio-stretch-card">
          <h3>{area.name}</h3>
          <p className="rio-stretch-meta">60 s after a hard day or a long run · 30 s when it is optional</p>
          <Disclosure title="Details">
            <p>{area.howTo}</p>
          </Disclosure>
        </article>
      ))}
    </>
  );
}
