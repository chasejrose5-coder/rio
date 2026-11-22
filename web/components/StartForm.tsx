"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer, PhotoCredit } from "./Footer";
import { PageMeaning } from "./PageMeaning";
import { PageSkeleton } from "./PageSkeleton";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { rememberLanding } from "@/lib/landing";
import {
  homeQuery,
  linkFromParams,
  planHasScore,
  sameSeason,
  startFormDefaults,
  startShouldGoHome,
  type SeasonInputs,
} from "@/lib/start-form";
import { commitRaceTime, maskRaceTime, raceTimeError } from "@/lib/time-mask";
import type { CurrentSeason } from "@/lib/types";
import { ErrorText } from "./ErrorText";

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
  const router = useRouter();
  const [season, setSeason] = useState<CurrentSeason | null | undefined>(undefined);
  const [link, setLink] = useState<SeasonInputs | null | undefined>(undefined);
  const [fresh, setFresh] = useState(false);

  useEffect(() => {
    // The four inputs live in the URL. They are read once, the way a shared link arrives.
    const params = new URLSearchParams(window.location.search);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLink(linkFromParams(params));
    setFresh(params.get("new") === "1");
    void api.currentSeason().then(setSeason).catch(() => setSeason(null));
  }, []);

  const today = athlete?.today;
  const differs = link != null && link !== undefined && !sameSeason(season?.inputs, link);
  const goHome = startShouldGoHome(season?.inputs?.goal_date, today, differs, fresh);

  useEffect(() => {
    if (!today || season === undefined || link === undefined) return;
    const active = Boolean(season?.inputs?.goal_date && season.inputs.goal_date >= today);
    rememberLanding(active ? "/home" : "/start");
    if (goHome) router.replace("/home");
  }, [today, season, link, goHome, router]);

  if (!athlete?.today || season === undefined || link === undefined || goHome) {
    return <PageSkeleton title="Start" pageClass="page-start" />;
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
        <PageMeaning page="start" />
        <PhotoCredit onPhoto>Photo by Bohdan Hyrovych on Pexels</PhotoCredit>
        <Footer onPhoto />
      </main>
    </div>
  );
}

function DifferentSeason({ link }: { link: SeasonInputs }) {
  const router = useRouter();
  const { refresh } = useAuth();
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
      await refresh();
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
      {error ? <ErrorText>{error}</ErrorText> : null}
      <button type="button" className="rio-secondary" onClick={() => void adopt()} disabled={busy}>
        Use this season
      </button>
    </section>
  );
}

function StartFields({ today, behavior }: { today: string; behavior: string }) {
  const router = useRouter();
  const { refresh } = useAuth();
  const defaults = startFormDefaults(today, behavior);
  const [currentTime, setCurrentTime] = useState(defaults.currentTime);
  const [startDate, setStartDate] = useState(defaults.startDate);
  const [goalTime, setGoalTime] = useState(defaults.goalTime);
  const [goalDate, setGoalDate] = useState(defaults.goalDate);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const current = commitRaceTime(currentTime.trim());
    const goal = commitRaceTime(goalTime.trim());
    setCurrentTime(current);
    setGoalTime(goal);
    const timeProblem = raceTimeError(current) || raceTimeError(goal);
    if (timeProblem) {
      setError(timeProblem);
      return;
    }
    const submitted: SeasonInputs = {
      current_time: current,
      start_date: startDate.trim(),
      goal_time: goal,
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
      await refresh();
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
      {error ? <ErrorText>{error}</ErrorText> : null}
      <form onSubmit={onSubmit} noValidate>
        <div className="rio-start-grid">
          <Field
            id="current-time"
            label="Your 800 m time today"
            help="Your best recent 800 m, as m:ss.cc, like 2:02.00. A rough guess is fine."
          >
            <input
              id="current-time"
              placeholder="2:02.00"
              inputMode="decimal"
              value={currentTime}
              autoComplete="off"
              aria-describedby="current-time-help"
              onChange={(event) => setCurrentTime(maskRaceTime(event.target.value))}
              onBlur={() => setCurrentTime((value) => commitRaceTime(value))}
            />
          </Field>
          <Field id="start-date" label="Start date" help="The day this season starts.">
            <input
              id="start-date"
              type="date"
              value={startDate}
              autoComplete="off"
              aria-describedby="start-date-help"
              onChange={(event) => setStartDate(event.target.value)}
              onClick={openDatePicker}
            />
          </Field>
          <Field
            id="goal-time"
            label="800 m time you're aiming for"
            help="The race time you want on your goal date. Same m:ss.cc format, like 1:58.00."
          >
            <input
              id="goal-time"
              placeholder="1:58.00"
              inputMode="decimal"
              value={goalTime}
              autoComplete="off"
              aria-describedby="goal-time-help"
              onChange={(event) => setGoalTime(maskRaceTime(event.target.value))}
              onBlur={() => setGoalTime((value) => commitRaceTime(value))}
            />
          </Field>
          <Field id="goal-date" label="Goal date" help="The day of the race.">
            <input
              id="goal-date"
              type="date"
              value={goalDate}
              autoComplete="off"
              aria-describedby="goal-date-help"
              onChange={(event) => setGoalDate(event.target.value)}
              onClick={openDatePicker}
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

function openDatePicker(event: { currentTarget: HTMLInputElement }) {
  const input = event.currentTarget;
  if (typeof input.showPicker !== "function") return;
  try {
    input.showPicker();
  } catch {
    /* Unsupported, already open, or not allowed from this focus. */
  }
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
