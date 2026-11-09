"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { Footer, PhotoCredit } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { TrackArt } from "./TrackArt";
import { ApiError, api } from "@/lib/api";
import type { HomeResponse, WorkoutCard } from "@/lib/types";

const MARKS: Record<string, string> = {
  on_track: "On track",
  not_hitting: "Not hitting",
  smashing: "Smashing",
};

function phaseText(phase: string | undefined): string {
  const text = (phase || "").trim();
  if (!text || text === "—") return "—";
  return `Phase ${text}`;
}

function markText(mark: { week?: number; mark?: string } | null | undefined): string {
  if (!mark || typeof mark.week !== "number" || !mark.mark || !(mark.mark in MARKS)) {
    return "No timed run yet";
  }
  return `Week ${mark.week} · ${MARKS[mark.mark]}`;
}

function headline(days: number | null | undefined, goal: string): ReactNode {
  if (typeof days === "number") {
    const unit = days === 1 ? "day" : "days";
    return (
      <>
        <span className="rio-display-num">{days}</span>
        <span className="rio-display-rest">
          {" "}
          {unit} to {goal || "goal"}
        </span>
      </>
    );
  }
  return "—";
}

function WorkoutFacts({ card, title }: { card: WorkoutCard; title: string }) {
  const facts = card.facts;
  const prescription = card.prescription;
  return (
    <div className="rio-track-facts">
      <div className="rio-track-fact">
        <p className="rio-mark-label">{title}</p>
        <p className="rio-track-day">
          {card.day_of_week || "—"}
          <span className="rio-track-sub">{card.shown_date || card.date || ""}</span>
        </p>
      </div>
      <Fact label="Distance" value={facts?.distance || "—"} />
      <Fact label="Pace" value={facts?.pace || "—"} />
      <Fact label="Rest" value={facts?.rest || "—"} />
      <Fact label="Reps" value={facts?.reps || "—"} />
      {card.label ? <p className="rio-pace-line">{card.label}</p> : null}
      {prescription?.line ? <p className="rio-pace-line">{prescription.line}</p> : null}
      {prescription?.tolerance ? <p className="rio-pace-range">Tolerance {prescription.tolerance}</p> : null}
      {prescription?.block ? <p className="rio-pace-block">Block {prescription.block}</p> : null}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rio-track-fact">
      <p className="rio-mark-label">{label}</p>
      <p className="rio-track-fact-value">{value}</p>
    </div>
  );
}

export function HomeView() {
  return (
    <RequireUser>
      <HomeBody />
    </RequireUser>
  );
}

function HomeBody() {
  const [home, setHome] = useState<HomeResponse | null>(null);
  const [error, setError] = useState("");
  const [offer, setOffer] = useState(false);

  async function load(justGenerated = false) {
    const body = await api.home(justGenerated);
    setHome(body);
    setOffer(body.strava_offer);
  }

  useEffect(() => {
    const generated = new URLSearchParams(window.location.search).get("just_generated") === "true";
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(generated).catch((caught) => {
      setError(caught instanceof ApiError ? caught.message : "Home could not be loaded.");
    });
  }, []);

  return (
    <div className="page-home">
      <Nav />
      <main className="rio-stagger">
        {error ? <p className="rio-error">{error}</p> : null}
        {home ? <HomeMain home={home} offer={offer} onDismiss={() => setOffer(false)} reload={() => void load(false)} /> : null}
        <PhotoCredit onPhoto>Photo by Gaby Lopez on Pexels</PhotoCredit>
        <Footer onPhoto />
      </main>
    </div>
  );
}

function HomeMain({
  home,
  offer,
  onDismiss,
  reload,
}: {
  home: HomeResponse;
  offer: boolean;
  onDismiss: () => void;
  reload: () => void;
}) {
  const season = home.season;
  const name = home.athlete.display_name?.trim();
  const planLine = name ? `${name}'s plan` : "";

  if (!season) {
    return (
      <>
        <header className="rio-hero rio-home-hero">
          <h1>Home</h1>
          {home.hello ? <p className="rio-hello">{home.hello}</p> : null}
        </header>
        {home.copy ? <p className="rio-note">{home.copy}</p> : null}
        <Link className="rio-secondary" href="/start">
          Generate season plan
        </Link>
      </>
    );
  }

  const todayWorkout = season.next?.date === home.today;
  const showedPhase = Boolean(season.phase?.collapsed);
  const workoutIndex = `${showedPhase ? "02" : "01"}  /  ${todayWorkout ? "Today's workout" : "Next workout"}`;
  const upcomingIndex = `${showedPhase ? "03" : "02"}  /  Next 3 days`;
  const panel = season.phase?.panel;

  return (
    <>
      {offer ? <StravaOffer onDismiss={onDismiss} /> : null}
      <header className="rio-hero rio-home-hero">
        <div className="rio-home-grid">
          <div className="rio-home-copy">
            <h1 className="rio-display">{headline(season.view.days_remaining, season.inputs.goal_time)}</h1>
            {home.hello ? <p className="rio-hello">{home.hello}</p> : null}
            {planLine ? <p className="rio-hello-plan">{planLine}</p> : null}
          </div>
          <div className="rio-hero-art">
            <TrackArt />
          </div>
        </div>
      </header>
      <div className="rio-stat-row rio-stat-words">
        <Stat label="Training block" value={phaseText(season.view.phase)} />
        <Stat label="Last timed effort" value={markText(season.view.mark)} />
        <Stat label="This week" value={season.view.focus || "—"} />
        <Stat label="Progress status" value={season.pace_status || "No runs yet"} />
      </div>
      <div className="rio-glossary rio-soft-card">
        <p>A training block is one phase of the season.</p>
        <p>A timed effort is a run you logged.</p>
        <p>Times use minutes:seconds.tenths, like 2:05.0.</p>
      </div>
      {showedPhase && season.phase ? (
        <section>
          <p className="rio-index rio-index-pad">01  /  Current phase</p>
          <details className="rio-phase-details">
            <summary>{season.phase.collapsed}</summary>
            <div className="rio-phase-panel">
              {panel?.headline ? <p className="rio-phase-headline">{panel.headline}</p> : null}
              {panel?.focus ? <p className="rio-phase-focus">{panel.focus}</p> : null}
              {panel?.days && panel.days.length > 0 ? (
                <ol className="rio-week-strip" aria-label="This week">
                  {panel.days.map((day) => (
                    <li key={`${day.short}-${day.role}`} className={`rio-week-chip is-${day.role || ""}`}>
                      <strong>{day.short}</strong>
                      <span>{roleWord(day.role)}</span>
                    </li>
                  ))}
                </ol>
              ) : null}
              {panel?.steps && panel.steps.length > 0 ? (
                <p className="rio-phase-progress">
                  {panel.steps.map((step, index) => (
                    <span key={step.label} className="rio-phase-step">
                      {index > 0 ? <span className="rio-phase-arrow">→</span> : null}
                      <em>{step.label}</em>
                      {step.text}
                    </span>
                  ))}
                </p>
              ) : null}
              {panel?.marks ? <p className="rio-phase-caption">{panel.marks}</p> : null}
              {panel?.note ? <p className="rio-phase-caption">{panel.note}</p> : null}
            </div>
          </details>
        </section>
      ) : null}
      {season.notes.map((item) => (
        <Insight key={item.date} date={item.date} note={item.note} onDone={reload} />
      ))}
      <section className="rio-home-today">
        <p className="rio-index">{workoutIndex}</p>
        {season.next ? (
          <Link className="rio-hit" href={`/session?date=${season.next.date || ""}`}>
            <WorkoutFacts card={season.next} title={todayWorkout ? "Today's workout" : "Next workout"} />
          </Link>
        ) : (
          <p className="rio-empty">No workout left in this plan.</p>
        )}
      </section>
      <p className="rio-index rio-index-pad">{upcomingIndex}</p>
      <div className="rio-next3">
        {(season.next_days || []).map((day) => (
          <DayCard key={day.date} card={day} />
        ))}
      </div>
      <div className="rio-quick">
        <Link href="/plan">Plan</Link>
        <Link href="/activity">Activity</Link>
        <Link href="/library">Library</Link>
        <Link href="/more">More</Link>
      </div>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rio-stat-tile">
      <p className="rio-mark-label">{label}</p>
      <p className="rio-stat-value">{value}</p>
    </div>
  );
}

function roleWord(role: string | undefined): string {
  if (role === "hard") return "Hard";
  if (role === "easy") return "Easy";
  if (role === "long") return "Long";
  if (role === "race") return "Race";
  if (role === "off") return "Off";
  return role || "";
}

function DayCard({ card }: { card: WorkoutCard }) {
  const body = (
    <div className="rio-mini">
      <div className="rio-mini-dow">{card.day_of_week || "—"}</div>
      <div className="rio-mini-date">{card.shown_date || card.date}</div>
      <div className="rio-mini-work">{card.label || "—"}</div>
      {card.prescription?.line ? <p className="rio-pace-line">{card.prescription.line}</p> : null}
      {card.prescription?.tolerance ? <p className="rio-pace-range">Tolerance {card.prescription.tolerance}</p> : null}
      {card.prescription?.block ? <p className="rio-pace-block">Block {card.prescription.block}</p> : null}
    </div>
  );
  if (!card.template_id || !card.date) return body;
  return (
    <Link className="rio-hit" href={`/session?date=${card.date}`}>
      {body}
    </Link>
  );
}

function Insight({
  date,
  note,
  onDone,
}: {
  date: string;
  note: { headline?: string; body?: string; carry_forward?: string };
  onDone: () => void;
}) {
  const [error, setError] = useState("");
  return (
    <section className="rio-insight">
      <p className="rio-insight-headline">{note.headline}</p>
      <p>{note.body}</p>
      {note.carry_forward ? (
        <details>
          <summary>Carry forward</summary>
          <p>{note.carry_forward}</p>
        </details>
      ) : null}
      <button
        type="button"
        className="rio-secondary"
        onClick={() => {
          void api
            .viewNote(date, note)
            .then(onDone)
            .catch((caught) => setError(caught instanceof ApiError ? caught.message : "That note could not be saved."));
        }}
      >
        Got it
      </button>
      {error ? <p className="rio-error">{error}</p> : null}
    </section>
  );
}

function StravaOffer({ onDismiss }: { onDismiss: () => void }) {
  const [error, setError] = useState("");

  return (
    <section className="rio-soft-card rio-strava-offer">
      <h2>Your plan is ready.</h2>
      <p>Connect Strava so your runs show up.</p>
      <button
        type="button"
        className="rio-primary"
        onClick={() => {
          void api
            .stravaConnect()
            .then((body) => {
              if (body.url) window.location.assign(body.url);
            })
            .catch((caught) => setError(caught instanceof ApiError ? caught.message : "Strava could not be opened."));
        }}
      >
        Connect Strava
      </button>
      <button
        type="button"
        className="rio-secondary"
        onClick={() => {
          void api
            .dismissStrava()
            .then(onDismiss)
            .catch((caught) => setError(caught instanceof ApiError ? caught.message : "That could not be saved."));
        }}
      >
        Not now
      </button>
      {error ? <p className="rio-error">{error}</p> : null}
    </section>
  );
}
