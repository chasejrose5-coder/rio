"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer, PhotoCredit } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  homeQuery,
  linkFromParams,
  planHasScore,
  sameSeason,
  startFormDefaults,
  type SeasonInputs,
} from "@/lib/start-form";
import type { CurrentSeason } from "@/lib/types";

const SCORE = "season plan has a score";

export function StartForm() {
  return (
    <RequireUser>
      <StartBody />
    </RequireUser>
  );
}

function StartBody() {
  const { athlete } = useAuth();
  const [season, setSeason] = useState<CurrentSeason | null | undefined>(undefined);
  const [link, setLink] = useState<SeasonInputs | null>(null);

  useEffect(() => {
    // The four inputs live in the URL. They are read once, the way a shared link arrives.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLink(linkFromParams(new URLSearchParams(window.location.search)));
    void api.currentSeason().then(setSeason).catch(() => setSeason(null));
  }, []);

  if (!athlete?.today || season === undefined) {
    return <p className="rio-wait">Loading</p>;
  }

  const behavior = athlete.prefs.start_date === "sunday" ? "sunday" : "today";
  const different = link != null && !sameSeason(season?.inputs, link);

  return (
    <div className="page-start">
      <Nav />
      <main>
        {different && link ? <DifferentSeason link={link} /> : null}
        <StartFields
          key={`${athlete.today}|${behavior}`}
          today={athlete.today}
          behavior={behavior}
        />
        <PhotoCredit onPhoto>Photo by Bohdan Hyrovych on Pexels</PhotoCredit>
        <Footer onPhoto />
      </main>
    </div>
  );
}

function DifferentSeason({ link }: { link: SeasonInputs }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function adopt() {
    setBusy(true);
    setError("");
    try {
      const saved = await api.createSeason(link);
      if (planHasScore(saved)) {
        setError(SCORE);
        return;
      }
      const inputs = saved.inputs || link;
      router.push(`/home?${homeQuery(inputs, false)}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "This account could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rio-link-note">
      <p>This link names a different season. Your saved season was left as it is.</p>
      {error ? <p className="rio-error">{error}</p> : null}
      <button type="button" className="rio-secondary" onClick={() => void adopt()} disabled={busy}>
        Use this season
      </button>
    </section>
  );
}

function StartFields({ today, behavior }: { today: string; behavior: string }) {
  const router = useRouter();
  const defaults = startFormDefaults(today, behavior);
  const [currentTime, setCurrentTime] = useState(defaults.currentTime);
  const [startDate, setStartDate] = useState(defaults.startDate);
  const [goalTime, setGoalTime] = useState(defaults.goalTime);
  const [goalDate, setGoalDate] = useState(defaults.goalDate);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const submitted: SeasonInputs = {
      current_time: currentTime.trim(),
      start_date: startDate.trim(),
      goal_time: goalTime.trim(),
      goal_date: goalDate.trim(),
    };
    setBusy(true);
    setError("");
    try {
      const saved = await api.createSeason(submitted);
      if (planHasScore(saved)) {
        setError(SCORE);
        return;
      }
      const inputs = saved.inputs || submitted;
      router.push(`/home?${homeQuery(inputs, true)}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rio-goal-card">
      <header className="rio-hero rio-start-hero">
        <h1>Start</h1>
        <p className="rio-range">Your 800 m time today, the day you start, the time you want, and the race date.</p>
      </header>
      {error ? <p className="rio-error">{error}</p> : null}
      <form onSubmit={onSubmit} noValidate>
        <div className="rio-start-grid">
          <Field
            id="current-time"
            label="Your 800 m time today"
            help="Your best recent 800 metres, as minutes:seconds.tenths. A rough guess is fine."
          >
            <input
              id="current-time"
              placeholder="2:05.0"
              value={currentTime}
              autoComplete="off"
              aria-describedby="current-time-help"
              onChange={(event) => setCurrentTime(event.target.value)}
            />
          </Field>
          <Field id="start-date" label="Start date" help="The day this season starts.">
            <input
              id="start-date"
              value={startDate}
              autoComplete="off"
              aria-describedby="start-date-help"
              onChange={(event) => setStartDate(event.target.value)}
            />
          </Field>
          <Field
            id="goal-time"
            label="800 m time you're aiming for"
            help="The race time you want on your goal date. Same minutes:seconds.tenths format."
          >
            <input
              id="goal-time"
              placeholder="1:58.0"
              value={goalTime}
              autoComplete="off"
              aria-describedby="goal-time-help"
              onChange={(event) => setGoalTime(event.target.value)}
            />
          </Field>
          <Field id="goal-date" label="Goal date" help="The day of the race.">
            <input
              id="goal-date"
              value={goalDate}
              autoComplete="off"
              aria-describedby="goal-date-help"
              onChange={(event) => setGoalDate(event.target.value)}
            />
          </Field>
        </div>
        <button className="rio-primary" type="submit" disabled={busy}>
          Generate season plan
        </button>
      </form>
    </section>
  );
}

function Field({ id, label, help, children }: { id: string; label: string; help: string; children: React.ReactNode }) {
  return (
    <div className="rio-start-field">
      <label htmlFor={id}>{label}</label>
      {children}
      <p className="rio-field-help" id={`${id}-help`}>
        {help}
      </p>
    </div>
  );
}
