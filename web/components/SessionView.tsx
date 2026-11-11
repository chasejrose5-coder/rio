"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Expander } from "./Expander";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api, previewing } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { weekdayName } from "@/lib/plan";
import {
  PREP,
  acceptTimeKey,
  confirmCopy,
  filledTimes,
  fitSlots,
  needsOutcome,
  slotsFrom,
  watchlessSummary,
} from "@/lib/session";
import type { LoggedActivity, SessionResponse } from "@/lib/types";

type Mode = "loading" | "missing" | "nodate" | "bad" | "ready" | "activity" | "error";

export function SessionView() {
  return (
    <RequireUser>
      <SessionBody />
    </RequireUser>
  );
}

function SessionBody() {
  const params = useSearchParams();
  const date = params.get("date") || "";
  const activity = params.get("activity") || "";
  const [mode, setMode] = useState<Mode>("loading");
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [extra, setExtra] = useState<LoggedActivity | null>(null);
  const [problem, setProblem] = useState("");
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
      setMode("nodate");
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
    // The date and the activity id are the page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, activity]);

  const heading =
    mode === "activity" && extra
      ? weekdayName(extra.date) || "Activity"
      : mode === "ready" && session
        ? session.session.day_of_week || weekdayName(session.date) || "Session"
        : "Session";
  const range = mode === "activity" && extra ? extra.date : mode === "ready" && session ? session.shown_date : "";

  const { athlete } = useAuth();
  const compact = athlete?.prefs.compact === true;
  return (
    <div className={compact ? "page-session is-compact" : "page-session"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>{heading}</h1>
          {range ? <p className="rio-range">{range}</p> : null}
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
        {mode === "error" ? <p className="rio-error">{problem}</p> : null}
        {mode === "activity" && extra ? <ActivityCard row={extra} /> : null}
        {mode === "ready" && session ? <Workout session={session} onSaved={() => void load()} /> : null}
        <Footer />
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

function Workout({ session, onSaved }: { session: SessionResponse; onSaved: () => void }) {
  const prescription = session.prescription;
  const note = session.note && session.viewed !== true ? session.note : null;
  return (
    <>
      <section className="rio-card">
        <div className={session.match ? "rio-session-split" : undefined}>
          <div>
            <p className="rio-mark-label">Workout</p>
            <h2 className="rio-week-title">{session.label}</h2>
            {session.show_id && session.session.template_id ? (
              <p className="rio-template-id">{session.session.template_id}</p>
            ) : null}
          </div>
          {session.match ? (
            <div className="rio-supplied">
              <p className="rio-mark-label">Intervals</p>
              {session.match.reps ? <Field label="Reps" value={session.match.reps} /> : null}
              {session.match.work ? <Field label="Work" value={session.match.work} /> : null}
              {session.match.heart_rate ? <Field label="Avg HR" value={session.match.heart_rate} /> : null}
            </div>
          ) : null}
        </div>
        {prescription?.line ? (
          <div className="rio-pace">
            <p className="rio-pace-line">{prescription.line}</p>
            {prescription.tolerance ? <p className="rio-pace-range">Tolerance {prescription.tolerance}</p> : null}
            {prescription.block ? <p className="rio-pace-block">Block {prescription.block}</p> : null}
          </div>
        ) : null}
        <Field label="Structure" value={session.structure || "—"} />
        <Field label="Target outcome" value={session.target || "—"} />
        <Prep />
        {session.heart_rate ? <Field label="Avg HR" value={session.heart_rate} /> : null}
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
      {session.logging === "done" ? (
        <Watchless session={session} onSaved={onSaved} />
      ) : session.boxes > 0 ? (
        <ResultForm key={`${session.digest}:${session.summary}`} session={session} onSaved={onSaved} />
      ) : null}
      {note?.headline && note.body ? <Insight session={session} note={note} onSaved={onSaved} /> : null}
    </>
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

function Prep() {
  return (
    <div className="rio-prep">
      {PREP.map((block) => (
        <section className="rio-prep-block" key={block.title}>
          <p className="rio-mark-label">{block.title}</p>
          {"lines" in block ? (
            block.lines.map((line) => (
              <p className="rio-prep-line" key={line}>
                {line}
              </p>
            ))
          ) : (
            block.lead.map((lead, index) => (
              <div key={lead}>
                <p className="rio-prep-lead">{lead}</p>
                <ul className="rio-prep-list">
                  {block.groups[index].map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ))
          )}
        </section>
      ))}
    </div>
  );
}

function ResultForm({ session, onSaved }: { session: SessionResponse; onSaved: () => void }) {
  const { athlete } = useAuth();
  const count = session.boxes;
  const seeded = (session.seed || []).map((slot) => (slot == null ? "" : String(slot)));
  while (seeded.length < count) seeded.push("");
  const [values, setValues] = useState(seeded.slice(0, count));
  const [pending, setPending] = useState<{ text: string; slots: (number | null)[] } | null>(null);
  const [error, setError] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const [file, setFile] = useState("—");
  const [fileError, setFileError] = useState("");
  const [source, setSource] = useState<string | null>(null);
  const handled = useRef(filledTimes(seeded.slice(0, count)));
  const sourceRef = useRef<string | null>(null);
  const timer = useRef<number | null>(null);
  const admin = athlete?.role === "admin";

  useEffect(() => {
    if (!admin) return;
    void api
      .intervalFiles()
      .then((body) => setFiles(body.files || []))
      .catch(() => setFiles([]));
  }, [admin]);

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
      void commit(text, slots, sourceRef.current);
    }, 350);
  }

  async function commit(text: string, slots: (number | null)[], intervals: string | null) {
    if (previewing()) return;
    setError("");
    try {
      const saved = await api.postResult({ date: session.date, text, slots, intervals }, session.digest);
      setPending(null);
      onSaved();
      if (saved.insight?.status === "pending") {
        window.setTimeout(onSaved, 700);
        window.setTimeout(onSaved, 1600);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "That result could not be saved.");
    }
  }

  async function chooseFile(name: string) {
    setFile(name);
    setFileError("");
    if (name === "—") {
      sourceRef.current = null;
      setSource(null);
      return;
    }
    try {
      const body = await api.intervalFill(name);
      sourceRef.current = body.source || name;
      setSource(sourceRef.current);
      const next = fitSlots(body.times, count);
      setValues(next);
      schedule(next);
    } catch (caught) {
      setSource(null);
      setFileError(caught instanceof ApiError ? caught.message : `Could not read ${name}.`);
    }
  }

  return (
    <section className="rio-result">
      <p className="rio-settings-note">Times save as you type.</p>
      <p className="rio-mark-label">Result</p>
      {admin ? (
        <label className="rio-file">
          Intervals file
          <select value={file} onChange={(event) => void chooseFile(event.target.value)}>
            <option value="—">—</option>
            {files.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {fileError ? <p className="rio-empty">{fileError}</p> : null}
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
          <button type="button" className="rio-primary" onClick={() => void commit(pending.text, pending.slots, source)}>
            Confirm
          </button>
          <button type="button" className="rio-secondary" onClick={() => setPending(null)}>
            Cancel
          </button>
        </div>
      ) : null}
      {error ? <p className="rio-error">{error}</p> : null}
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
  if (same?.completed) {
    return <p className="rio-week-meta">{watchlessSummary(same)}</p>;
  }

  async function send(missed: boolean) {
    if (previewing()) return;
    const outcomeError = missed ? "" : needsOutcome(session.quality, choice);
    if (outcomeError) {
      setError(outcomeError);
      return;
    }
    setError("");
    try {
      await api.watchless({ date: session.date, outcome: choice, time, missed });
      setPending(false);
      onSaved();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "That workout could not be saved.");
    }
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
      {same?.missed ? <p className="rio-settings-note">Couldn&apos;t finish. Done still completes this workout.</p> : null}
      {session.quality ? (
        <div className="rio-done-choices">
          {["Behind", "On target", "Ahead"].map((label) => (
            <button key={label} type="button" className={choice === label ? "rio-primary" : "rio-secondary"} onClick={() => setChoice(label)}>
              {label}
            </button>
          ))}
        </div>
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
        <button type="button" className="rio-primary" onClick={done}>
          Done
        </button>
        <button type="button" className="rio-secondary" onClick={() => void send(true)}>
          Couldn&apos;t finish
        </button>
        <button type="button" className="rio-text-link" onClick={() => setOpen((value) => !value)}>
          Add a time
        </button>
      </div>
      {pending ? (
        <div className="rio-confirm">
          <p className="rio-week-meta">{confirmCopy("workout")}</p>
          <button type="button" className="rio-primary" onClick={() => void send(false)}>
            Confirm
          </button>
          <button type="button" className="rio-secondary" onClick={() => setPending(false)}>
            Cancel
          </button>
        </div>
      ) : null}
      {error ? <p className="rio-error">{error}</p> : null}
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
      {error ? <p className="rio-error">{error}</p> : null}
    </section>
  );
}
