"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclosure } from "./Disclosure";
import { ApiError, api, previewing } from "@/lib/api";
import {
  dayBlocks,
  levelOn,
  type DayBlock,
  type LevelName,
} from "@/lib/injury-content";
import type { StretchSession } from "@/lib/stretch-content";
import type { InjuryState } from "@/lib/types";
import { LoadError } from "./ErrorText";

function label(level: LevelName): string {
  if (level === "easy") return "Easy";
  if (level === "medium") return "Medium";
  return "Hard";
}

export function InjuryDay({ date }: { date: string }) {
  const [state, setState] = useState<InjuryState | null>(null);
  const [sessions, setSessions] = useState<StretchSession[]>([]);
  const [offline, setOffline] = useState(false);
  const [problem, setProblem] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    let live = true;
    Promise.all([
      api.injury().catch((caught: unknown) => {
        if (caught instanceof ApiError && (caught.status === 404 || caught.status === 503)) return null;
        throw caught;
      }),
      api.currentSeason().catch(() => null),
    ])
      .then(([injury, season]) => {
        if (!live) return;
        setState(injury);
        setOffline(injury == null);
        const planSessions = season?.plan?.sessions;
        setSessions(Array.isArray(planSessions) ? planSessions : []);
      })
      .catch((caught: unknown) => {
        if (!live) return;
        setProblem(caught instanceof ApiError ? caught.message : "Injury prevention could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [date, attempt]);

  const areas = (state?.areas ?? []).map((area) => ({
    areaId: area.area_id,
    level: levelOn(area.level, area.anchor_on, date),
  }));
  const blocks = date ? dayBlocks(date, sessions, areas) : [];
  const done = new Set(
    (state?.completions ?? []).filter((row) => row.date.slice(0, 10) === date).map((row) => row.block_id),
  );
  const canSave = state != null && !previewing() && state.today === date;

  async function run(key: string, work: () => Promise<InjuryState>) {
    if (busy) return;
    setBusy(key);
    setProblem("");
    try {
      setState(await work());
      setOffline(false);
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "That could not be saved.");
    } finally {
      setBusy("");
    }
  }

  return (
    <section className="rio-recover-block" aria-label="Injury prevention">
      <p className="rio-mark-label">Injury prevention</p>
      {blocks.length === 0 ? (
        <p className="rio-note">None today. Race day and the day before stay clear, and the other days rotate.</p>
      ) : (
        blocks.map((block) => (
          <Block
            key={block.id}
            block={block}
            done={done.has(block.id)}
            canSave={canSave}
            busy={busy === block.id}
            onDone={() => void run(block.id, () => api.injuryComplete(block.id, !done.has(block.id)))}
            onStep={() => void run(`${block.id}-back`, () => api.injuryStepBack(block.id))}
            stepBusy={busy === `${block.id}-back`}
          />
        ))
      )}
      {offline ? <p className="rio-note">Saving is unavailable until the injury-prevention tables are in place.</p> : null}
      {problem ? <LoadError message={problem} onRetry={() => setAttempt((value) => value + 1)} /> : null}
      <p className="rio-stretch-link">
        <Link href="/recovery">Choose areas on Recovery</Link>
      </p>
    </section>
  );
}

function Block({
  block,
  done,
  canSave,
  busy,
  onDone,
  onStep,
  stepBusy,
}: {
  block: DayBlock;
  done: boolean;
  canSave: boolean;
  busy: boolean;
  onDone: () => void;
  onStep: () => void;
  stepBusy: boolean;
}) {
  return (
    <article className="rio-recover-item">
      <h3>
        {block.title}
        {block.level ? <span> · {label(block.level)}</span> : null}
      </h3>
      {block.boneMessage ? <p className="rio-medical">{block.boneMessage}</p> : null}
      {block.exercises.length ? (
        <>
          <ul className="rio-prep-list">
            {block.exercises.map((item) => (
              <li key={item.exercise.id}>
                <strong>
                  {item.exercise.name} · {item.dose}
                </strong>
              </li>
            ))}
          </ul>
          <Disclosure title="Details">
            {block.exercises.map((item) => (
              <p key={`${item.exercise.id}-how`}>
                <strong>{item.exercise.name}.</strong> {item.exercise.howTo}
              </p>
            ))}
          </Disclosure>
        </>
      ) : null}
      {canSave && !block.boneMessage ? (
        <div className="rio-done-row">
          <button type="button" className={done ? "rio-secondary" : "rio-primary"} disabled={busy} onClick={onDone}>
            {done ? "Done" : "Mark done"}
          </button>
          {block.id !== "general" && block.level && block.level !== "easy" ? (
            <button type="button" className="rio-secondary" disabled={stepBusy} onClick={onStep}>
              It hurt, step back a level
            </button>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
