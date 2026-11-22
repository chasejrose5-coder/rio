"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BikeCard } from "./BikeSwap";
import { CoreDay } from "./CoreDay";
import { Disclosure } from "./Disclosure";
import { Expander } from "./Expander";
import { FoamDay } from "./FoamDay";
import { InjuryDay } from "./InjuryDay";
import { HeartPace } from "./HeartPace";
import { StretchLink } from "./StretchLink";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api, isSignedOut, previewing } from "@/lib/api";
import { createSaveQueue } from "@/lib/save-queue";
import { useAuth } from "@/lib/auth";
import { CORE_DISCLAIMER } from "@/lib/core-content";
import { weekdayName } from "@/lib/plan";
import {
  acceptTimeKey,
  confirmCopy,
  filledTimes,
  needsOutcome,
  prepFor,
  slotsFrom,
  watchlessSummary,
  type PrepBlock,
} from "@/lib/session";
import type { BikeOffer, LoggedActivity, SessionResponse } from "@/lib/types";
import { ErrorText, LoadError } from "./ErrorText";
import { SaveFlash } from "./present/SaveLabel";

type Mode = "loading" | "missing" | "nodate" | "bad" | "ready" | "activity" | "error";

export function SessionView() {
  return (
    <RequireUser title="Session" pageClass="page-session">
      <SessionBody />
    </RequireUser>
  );
}

function SessionBody() {
  const { athlete, status } = useAuth();
  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  const params = useSearchParams();
  const date = params.get("date") || "";
  const activity = params.get("activity") || "";
  const [mode, setMode] = useState<Mode>("loading");
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [extra, setExtra] = useState<LoggedActivity | null>(null);
  const [problem, setProblem] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [rise, setRise] = useState(false);

  async function load() {
    if (activity) {
      try {
        const body = await api.activities();
        const row = (body.logged || []).find((item) => item.id === activity) || null;
        if (row && !row.matched) {
          setExtra(row);
          setMode("activity");
          return;
        }
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 404) {
          setMode("missing");
          return;
        }
        if (!date) {
          setProblem(caught instanceof ApiError ? caught.message : "That session could not be loaded.");
          setMode("error");
          return;
        }
      }
    }
    if (!date) {
      if (previewing()) {
        setMode("nodate");
        return;
      }
      try {
        const season = await api.currentSeason();
        setMode(season ? "nodate" : "missing");
      } catch (caught) {
        setProblem(caught instanceof ApiError ? caught.message : "That session could not be loaded.");
        setMode("error");
      }
      return;
    }
    try {
      const body = await api.session(date);
      setSession(body);
      setMode("ready");
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 404) {
        const missing = /no current season/i.test(caught.message);
        setMode(missing ? "missing" : "bad");
        return;
      }
      if (isSignedOut(caught) && statusRef.current !== "in") return;
      setProblem(caught instanceof ApiError ? caught.message : "That session could not be loaded.");
      setMode("error");
    }
  }

  useEffect(() => {
    const key = "rio-motion-page";
    const previous = window.sessionStorage.getItem(key);
    if (previous !== "session") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRise(true);
    }
    window.sessionStorage.setItem(key, "session");
    void load();
    // The date and the activity id are the page. attempt re-runs a failed load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, activity, attempt]);

  const heading =
    mode === "activity" && extra
      ? weekdayName(extra.date) || "Activity"
      : mode === "ready" && session
        ? session.session.day_of_week || weekdayName(session.date) || "Session"
        : "Session";
  const range = mode === "activity" && extra ? extra.date : mode === "ready" && session ? session.shown_date : "";

  const compact = athlete?.prefs.compact === true;
  return (
    <div className={compact ? "page-session rio-v3 is-compact" : "page-session rio-v3"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>{heading}</h1>
          {range ? <p className="rio-range">{range}</p> : null}
          {mode === "ready" && session ? (
            <>
              {session.label ? <h2 className="rio-range">{session.label}</h2> : null}
              {session.prescription?.line ? <p className="rio-hero-chip">{session.prescription.line}</p> : null}
              {session.prescription?.tolerance ? (
                <p className="rio-range">Target range {session.prescription.tolerance}</p>
              ) : null}
            </>
          ) : null}
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode === "missing" ? (
          <>
            <p className="rio-empty">Generate a season on Start.</p>
            <p className="rio-season-prompt">
              <Link href="/start">Generate season plan</Link>
            </p>
          </>
        ) : null}
        {mode === "nodate" ? <p className="rio-empty">Open a workout from Home or Plan.</p> : null}
        {mode === "bad" ? <p className="rio-empty">That session is not in this plan.</p> : null}
        {mode === "error" ? <LoadError message={problem} onRetry={() => setAttempt((value) => value + 1)} /> : null}
        {mode === "activity" && extra ? <ActivityCard row={extra} /> : null}
        {mode === "ready" && session ? (
          <Workout
            session={session}
            units={athlete?.prefs.units === "km" ? "km" : "miles"}
            onSaved={() => void load()}
          />
        ) : null}
        <Footer page="session" />
      </main>
    </div>
  );
}

function ActivityCard({ row }: { row: LoggedActivity }) {
  return (
    <section className="rio-card">
      <p className="rio-mark-label">Activity</p>
      <p className="rio-name">{row.name || "Activity"}</p>
      {row.reps ? (
        <>
          <p className="rio-mark-label">Reps</p>
          <p>{row.reps}</p>
        </>
      ) : null}
      {row.volume ? (
        <>
          <p className="rio-mark-label">Volume</p>
          <p>{row.volume}</p>
        </>
      ) : null}
      {row.heart_rate ? (
        <>
          <p className="rio-mark-label">Avg HR</p>
          <p>{row.heart_rate}</p>
        </>
      ) : null}
    </section>
  );
}

function clock(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function ZoneTime({ zones }: { zones: SessionResponse["zones"] }) {
  if (!zones?.zones?.length) return null;
  return (
    <section className="rio-zone-breakdown" aria-label="Time in zone">
      <p className="rio-mark-label">Time in zone</p>
      <ul className="rio-zone-list">
        {zones.zones.map((row) => (
          <li key={row.zone}>
            <p className="rio-zone-name">
              Zone {row.zone} · {row.name}
            </p>
            <p className="rio-zone-bpm">{clock(row.seconds)}</p>
          </li>
        ))}
      </ul>
      {zones.warning ? (
        <p className="rio-zone-warning" role="alert">
          {zones.warning}
        </p>
      ) : null}
    </section>
  );
}

function Workout({
  session,
  units,
  onSaved,
}: {
  session: SessionResponse;
  units: string;
  onSaved: () => void;
}) {
  const [offer, setOffer] = useState<BikeOffer | null>(null);
  const prescription = session.prescription;
  const note = session.note && session.viewed !== true ? session.note : null;
  const active = offer != null && (offer.offer || offer.swapped);
  const hideRun = offer?.swapped === true;
  const card = active && offer ? <BikeCard offer={offer} units={units} onOffer={setOffer} /> : null;

  useEffect(() => {
    let live = true;
    api
      .bike(session.date)
      .then((body) => {
        if (live) setOffer(body);
      })
      .catch((caught: unknown) => {
        if (!live) return;
        if (caught instanceof ApiError) setOffer(null);
      });
    return () => {
      live = false;
    };
  }, [session.date]);

  const log =
    !hideRun && session.logging === "done" ? (
      <Watchless session={session} onSaved={onSaved} />
    ) : !hideRun && session.boxes > 0 ? (
      <ResultForm key={`${session.digest}:${session.summary}`} session={session} onSaved={onSaved} />
    ) : null;

  const blocks = prepFor(session.session);
  const before = blocks.filter((block) => block.title !== "Cool-down" && block.title !== "Core");
  const cooldown = blocks.find((block) => block.title === "Cool-down");
  const corePrep = blocks.find((block) => block.title === "Core");

  return (
    <div className="rio-session-stack">
      {!hideRun && before.length ? (
        <section className="rio-session-group" aria-label="Before workout">
          <p className="rio-eyebrow">Before workout</p>
          {before.map((block) => (
            <Disclosure className="rio-session-box" title={block.title} key={block.title}>
              <PrepBody block={block} />
            </Disclosure>
          ))}
        </section>
      ) : null}
      <section className="rio-session-group" aria-label="Workout">
        <p className="rio-eyebrow">Workout</p>
        <section className="rio-card rio-session-box">
          <p className="rio-mark-label">Workout</p>
          {session.show_id && session.session.template_id ? (
            <p className="rio-template-id">{session.session.template_id}</p>
          ) : null}
          {session.match && !hideRun ? (
            <div className="rio-supplied">
              <p className="rio-mark-label">Logged run</p>
              {session.match.reps ? <Field label="Reps" value={session.match.reps} /> : null}
              {session.match.work ? <Field label="Work" value={session.match.work} /> : null}
              {session.match.heart_rate ? <Field label="Avg HR" value={session.match.heart_rate} /> : null}
            </div>
          ) : null}
          {!hideRun && (prescription?.block || prescription?.heart) ? (
            <div className="rio-pace">
              {prescription?.block ? <p className="rio-pace-block">Block {prescription.block}</p> : null}
              <HeartPace heart={prescription.heart} />
            </div>
          ) : null}
          {!hideRun ? (
            <Disclosure title="Details">
              <Field label="Structure" value={session.structure || "—"} />
              <Field label="Target outcome" value={session.target || "—"} />
            </Disclosure>
          ) : null}
          {log}
          {session.heart_rate ? <Field label="Avg HR" value={session.heart_rate} /> : null}
          <ZoneTime zones={session.zones} />
          <section className="rio-session-section">
            <p className="rio-mark-label">Reasons</p>
            {session.reasons.length ? (
              session.reasons.map((line) => (
                <p className="rio-reason" key={line}>
                  {line}
                </p>
              ))
            ) : (
              <p className="rio-empty">—</p>
            )}
          </section>
        </section>
        {active && offer ? <div className="rio-card rio-session-box">{card}</div> : null}
      </section>
      <section className="rio-session-group" aria-label="After workout">
        <p className="rio-eyebrow">After workout</p>
        <p className="rio-medical">{CORE_DISCLAIMER}</p>
        {!hideRun && cooldown ? (
          <Disclosure className="rio-session-box" title={cooldown.title}>
            <PrepBody block={cooldown} />
          </Disclosure>
        ) : null}
        <Disclosure className="rio-session-box" title="Core">
          {corePrep ? <PrepBody block={corePrep} /> : null}
          <CoreDay key={`${session.date}-core`} date={session.date} session={session.session} bare />
        </Disclosure>
        <FoamDay key={`${session.date}-foam`} date={session.date} session={session.session} />
        <Disclosure className="rio-session-box" title="Stretching">
          <StretchLink today={session.date} />
        </Disclosure>
        <Disclosure className="rio-session-box" title="Injury prevention">
          <InjuryDay key={session.date} date={session.date} bare />
        </Disclosure>
      </section>
      {note?.headline && note.body ? <Insight session={session} note={note} onSaved={onSaved} /> : null}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <section className="rio-session-section">
      <p className="rio-mark-label">{label}</p>
      <p className="rio-note">{value}</p>
    </section>
  );
}

function PrepBody({ block }: { block: PrepBlock }) {
  return (
    <>
      {(block.lines || []).map((line) => (
        <p className="rio-prep-line" key={line}>
          {line}
        </p>
      ))}
      {(block.lead || []).map((lead, index) => (
        <div key={lead}>
          <p className="rio-prep-lead">{lead}</p>
          {(block.groups?.[index] || []).length ? (
            <ul className="rio-prep-list">
              {(block.groups?.[index] || []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ))}
    </>
  );
}

function ResultForm({ session, onSaved }: { session: SessionResponse; onSaved: () => void }) {
  const count = session.boxes;
  const seeded = (session.seed || []).map((slot) => (slot == null ? "" : String(slot)));
  while (seeded.length < count) seeded.push("");
  const [values, setValues] = useState(seeded.slice(0, count));
  const [pending, setPending] = useState<{ text: string; slots: (number | null)[] } | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const handled = useRef(filledTimes(seeded.slice(0, count)));
  const timer = useRef<number | null>(null);
  const digestRef = useRef(session.digest);
  const queue = useRef(createSaveQueue<{ text: string; slots: (number | null)[] }>());

  function schedule(nextValues: string[]) {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      const text = filledTimes(nextValues);
      if (text === handled.current) return;
      handled.current = text;
      if (!text) {
        setPending(null);
        return;
      }
      const slots = slotsFrom(nextValues);
      if (session.confirm_adapt) {
        setPending({ text, slots });
        return;
      }
      requestSave(text, slots, "queue");
    }, 350);
  }

  function requestSave(text: string, slots: (number | null)[], mode: "once" | "queue") {
    if (previewing()) return;
    const flight = queue.current.push({ text, slots }, mode, async (next) => {
      setError("");
      try {
        const saved = await api.postResult({ date: session.date, text: next.text, slots: next.slots }, digestRef.current);
        if (saved.digest) digestRef.current = saved.digest;
        setPending(null);
        onSaved();
        if (saved.insight?.status === "pending") {
          window.setTimeout(onSaved, 700);
          window.setTimeout(onSaved, 1600);
        }
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "That result could not be saved.");
      }
    });
    if (!flight) return;
    setBusy(true);
    void flight.then(() => setBusy(false));
  }

  return (
    <section className="rio-result">
      <p className="rio-settings-note">Times save as you type.</p>
      <p className="rio-mark-label">Result</p>
      {count > 1 ? <p className="rio-rep-note">Enter the time for each rep.</p> : null}
      <div className={count > 1 ? "rio-result-grid" : "rio-result-one"}>
        {values.map((value, index) => (
          <label key={index}>
            {count > 1 ? `Rep ${index + 1}` : "Time"}
            <input
              inputMode="decimal"
              aria-label={count > 1 ? `Rep ${index + 1}` : "Time"}
              value={value}
              onChange={(event) => {
                const next = acceptTimeKey(value, event.target.value);
                const nextValues = values.map((item, itemIndex) => (itemIndex === index ? next : item));
                setValues(nextValues);
                schedule(nextValues);
              }}
            />
          </label>
        ))}
      </div>
      {session.summary ? <p className="rio-week-meta">{session.summary}</p> : null}
      {pending ? (
        <div className="rio-confirm">
          <p className="rio-week-meta">{confirmCopy("result")}</p>
          <button
            type="button"
            className="rio-primary"
            disabled={busy}
            aria-busy={busy}
            onClick={() => requestSave(pending.text, pending.slots, "once")}
          >
            Confirm
          </button>
          <button type="button" className="rio-secondary" onClick={() => setPending(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {error ? <ErrorText>{error}</ErrorText> : null}
      <SaveFlash busy={busy} error={error} />
    </section>
  );
}

function Watchless({ session, onSaved }: { session: SessionResponse; onSaved: () => void }) {
  const saved = session.actual;
  const same = saved && saved.template_id === session.session.template_id ? saved : null;
  const [choice, setChoice] = useState("");
  const [time, setTime] = useState("");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const queue = useRef(createSaveQueue<boolean>());
  if (same?.completed) {
    return <p className="rio-week-meta">{watchlessSummary(same)}</p>;
  }

  function send(missed: boolean) {
    if (previewing()) return;
    const outcomeError = missed ? "" : needsOutcome(session.quality, choice);
    if (outcomeError) {
      setError(outcomeError);
      return;
    }
    const flight = queue.current.push(missed, "once", async (flag) => {
      setError("");
      try {
        await api.watchless({ date: session.date, outcome: choice, time, missed: flag });
        setPending(false);
        onSaved();
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "That workout could not be saved.");
      }
    });
    if (!flight) return;
    setBusy(true);
    void flight.then(() => setBusy(false));
  }

  function done() {
    const outcomeError = needsOutcome(session.quality, choice);
    if (outcomeError) {
      setError(outcomeError);
      return;
    }
    if (session.quality && session.confirm_adapt && time.trim()) {
      setPending(true);
      setError("");
      return;
    }
    void send(false);
  }

  return (
    <section className="rio-watchless">
      {same?.missed ? <p className="rio-settings-note">Saved as couldn&apos;t finish. Finished after all? Tap Done.</p> : null}
      {session.quality ? (
        <div className="rio-done-choices">
          {["Behind", "On track", "Ahead"].map((label) => (
            <button key={label} type="button" className={choice === label ? "rio-primary" : "rio-secondary"} aria-pressed={choice === label} onClick={() => setChoice(label)}>
              {label}
            </button>
          ))}
        </div>
      ) : null}
      {session.quality ? (
        <p className="rio-settings-note">Behind: slower than the target. On track: within 3%. Ahead: faster.</p>
      ) : null}
      {open ? (
        <>
          <label htmlFor={`done-time-${session.date}`}>Time</label>
          <input
            id={`done-time-${session.date}`}
            placeholder="1:12.4"
            value={time}
            onChange={(event) => setTime(event.target.value)}
          />
          <p className="rio-settings-note">Optional. One clock time, like 1:12.4. Leave it blank to finish without one.</p>
        </>
      ) : null}
      <div className="rio-done-row">
        <button type="button" className="rio-primary" onClick={done} disabled={busy} aria-busy={busy}>
          Done
        </button>
        <button type="button" className="rio-secondary" onClick={() => send(true)} disabled={busy} aria-busy={busy}>
          Couldn&apos;t finish
        </button>
        <button type="button" className="rio-text-link" onClick={() => setOpen((value) => !value)}>
          Add a time
        </button>
      </div>
      {pending ? (
        <div className="rio-confirm">
          <p className="rio-week-meta">{confirmCopy("workout")}</p>
          <button type="button" className="rio-primary" onClick={() => send(false)} disabled={busy} aria-busy={busy}>
            Confirm
          </button>
          <button type="button" className="rio-secondary" onClick={() => setPending(false)}>
            Cancel
          </button>
        </div>
      ) : null}
      {error ? <ErrorText>{error}</ErrorText> : null}
    </section>
  );
}

function Insight({
  session,
  note,
  onSaved,
}: {
  session: SessionResponse;
  note: { headline?: string; body?: string; carry_forward?: string };
  onSaved: () => void;
}) {
  const [error, setError] = useState("");
  return (
    <section className="rio-insight">
      <p className="rio-insight-headline">{note.headline}</p>
      <p>{note.body}</p>
      {note.carry_forward ? (
        <Expander title="Carry forward">
          <p>{note.carry_forward}</p>
        </Expander>
      ) : null}
      <button
        type="button"
        className="rio-secondary"
        onClick={() => {
          void api
            .viewNote(session.date, note)
            .then(onSaved)
            .catch((caught) => setError(caught instanceof ApiError ? caught.message : "That note could not be saved."));
        }}
      >
        Got it
      </button>
      {error ? <ErrorText>{error}</ErrorText> : null}
    </section>
  );
}
