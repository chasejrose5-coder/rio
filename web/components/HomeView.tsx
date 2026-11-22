"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Disclosure } from "./Disclosure";
import { Expander } from "./Expander";
import { HeartPace } from "./HeartPace";
import { Footer, PhotoCredit } from "./Footer";
import { shareHero } from "./present/motion";
import { PageMeaning } from "./PageMeaning";
import { Nav } from "./Nav";
import { PreviewBanner } from "./PreviewBanner";
import { SkeletonBlocks } from "./PageSkeleton";
import { RequireUser } from "./RequireUser";
import { StretchLink } from "./StretchLink";
import { TrackArt } from "./TrackArt";
import { ApiError, api, isSignedOut, previewing, stopPreview } from "@/lib/api";
import { createSaveQueue } from "@/lib/save-queue";
import { useAuth } from "@/lib/auth";
import { takeIntroMark } from "@/lib/enter";
import { HR_PROMPT_KEY, heartPromptOpen, heartRateSatisfied, subscribeHeartRate } from "@/lib/landing";
import { pageShouldRise } from "@/lib/motion";
import { linkError } from "@/lib/plan";
import { shownName } from "@/lib/settings";
import type { HomeResponse, WorkoutCard } from "@/lib/types";
import { ErrorText, LoadError } from "./ErrorText";

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
        <span className="rio-display-num">
          <Countdown days={days} />
        </span>
        <span className="rio-display-rest">
          {" "}
          {unit} to your {goal || "goal"} 800 m
        </span>
      </>
    );
  }
  return "—";
}

function HomeCredit() {
  return (
    <PhotoCredit onPhoto href="https://www.pexels.com/photo/birds-eye-view-of-athletics-stadium-18588227/">
      Photo by Gaby Lopez on Pexels
    </PhotoCredit>
  );
}

function Countdown({ days }: { days: number }) {
  const text = String(days);
  return (
    <span className="rio-roll">
      {text.split("").map((digit, index) => (
        <span key={`${digit}-${index}`} style={{ animationDelay: `${index * 40}ms` }}>
          {digit}
        </span>
      ))}
    </span>
  );
}

function edgeClass(text: string): string {
  const value = text.toLowerCase();
  if (/\blong\b/.test(value)) return "is-long";
  if (/\beasy\b/.test(value)) return "is-easy";
  if (/\bspeed\b/.test(value) || /×/.test(text)) return "is-speed";
  return "";
}

function WorkoutFacts({ card, title, showId }: { card: WorkoutCard; title: string; showId: boolean }) {
  const facts = card.facts;
  const prescription = card.prescription;
  const templateId = (card.template_id || "").trim();
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
      {showId && templateId ? <div className="rio-template-id rio-track-id">{templateId}</div> : null}
      {prescription?.line ? <p className="rio-pace-line">{prescription.line}</p> : null}
      {prescription?.tolerance ? <p className="rio-pace-range">Target range {prescription.tolerance}</p> : null}
      {prescription?.block ? <p className="rio-pace-block">Block {prescription.block}</p> : null}
      <HeartPace heart={prescription?.heart} />
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
    <RequireUser variant="home">
      <HomeBody />
    </RequireUser>
  );
}

function HomeBody() {
  const router = useRouter();
  const { status } = useAuth();
  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);
  const [home, setHome] = useState<HomeResponse | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [linkProblem, setLinkProblem] = useState("");
  const [offer, setOffer] = useState(false);
  const [rise, setRise] = useState(false);
  const [readOnly, setReadOnly] = useState(false);

  useEffect(() => {
    const key = "rio-motion-page";
    const previous = window.sessionStorage.getItem(key);
    if (pageShouldRise(previous, "home")) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRise(true);
    }
    window.sessionStorage.setItem(key, "home");
  }, []);

  async function load(justGenerated = false) {
    const body = await api.home(justGenerated);
    setHome(body);
    setOffer(body.strava_offer);
    if (takeIntroMark()) void api.patchSettings({ intro_seen: true }).catch(() => undefined);
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("preview") === "test") window.sessionStorage.setItem("rio_test_preview", "1");
    const linked = linkError(params);
    if (linked) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLinkProblem(linked);
      return;
    }
    setReadOnly(previewing());
    const generated = params.get("just_generated") === "true";
    void load(generated).catch((caught) => {
      if (isSignedOut(caught) && statusRef.current !== "in") return;
      if (caught instanceof ApiError && caught.status === 403 && previewing()) {
        stopPreview();
        router.replace("/home");
        return;
      }
      setError(caught instanceof ApiError ? caught.message : "Home could not be loaded.");
    });
  }, [router, attempt]);

  const compact = home?.athlete.prefs.compact === true;
  return (
    <div className={compact ? "page-home rio-v3 is-compact" : "page-home rio-v3"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        {readOnly || home?.preview?.active ? <PreviewBanner banner={home?.preview?.banner} /> : null}
        {linkProblem ? (
          <header className="rio-hero rio-home-hero">
            <h1>Home</h1>
            <ErrorText>{linkProblem}</ErrorText>
            <HomeCredit />
          </header>
        ) : null}
        {error ? <LoadError message={error} onRetry={() => setAttempt((value) => value + 1)} /> : null}
        {!home && !linkProblem && !error ? <SkeletonBlocks variant="home" /> : null}
        {home && !linkProblem ? (
          <div className="rio-home-stack">
            <HeartRatePrompt />
            <HomeMain home={home} offer={offer} readOnly={readOnly} onDismiss={() => setOffer(false)} reload={() => void load(false)} />
          </div>
        ) : null}
        <PageMeaning page="home" />
        <Footer />
      </main>
    </div>
  );
}

function HeartRatePrompt() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let live = true;
    const check = () => {
      const dismissed = window.sessionStorage.getItem(HR_PROMPT_KEY) === "1";
      if (heartRateSatisfied()) {
        setOpen(false);
        return;
      }
      void api
        .heartRate()
        .then((profile) => {
          if (!live) return;
          setOpen(heartPromptOpen(profile, dismissed, heartRateSatisfied()));
        })
        .catch(() => undefined);
    };
    check();
    const stop = subscribeHeartRate(() => {
      if (heartRateSatisfied()) setOpen(false);
    });
    window.addEventListener("focus", check);
    return () => {
      live = false;
      stop();
      window.removeEventListener("focus", check);
    };
  }, []);

  if (!open) return null;
  return (
    <section className="rio-soft-card rio-hr-prompt" aria-label="Heart rate">
      <h2>Add your heart rate</h2>
      <p>Resting and max heart rate set the zones on easy, tempo, and threshold days.</p>
      <Link className="rio-primary" href="/heart-rate">
        Add heart rate
      </Link>
      <button
        type="button"
        className="rio-secondary"
        onClick={(event) => {
          window.sessionStorage.setItem(HR_PROMPT_KEY, "1");
          event.currentTarget.closest("section")?.classList.add("is-leaving");
          window.setTimeout(() => setOpen(false), 240);
        }}
      >
        Not now
      </button>
    </section>
  );
}

function HomeMain({
  home,
  offer,
  readOnly,
  onDismiss,
  reload,
}: {
  home: HomeResponse;
  offer: boolean;
  readOnly: boolean;
  onDismiss: () => void;
  reload: () => void;
}) {
  const season = home.season;
  const name = shownName(home.athlete.display_name || "", String(home.athlete.prefs.preferred || ""));
  const planLine = name ? `${name}'s plan` : "";

  if (home.broken) {
    return (
      <>
        <header className="rio-hero rio-home-hero">
          <h1>Home</h1>
          {home.hello ? <p className="rio-hello">{home.hello}</p> : null}
          <HomeCredit />
        </header>
        <p className="rio-empty">—</p>
      </>
    );
  }

  if (!season) {
    return (
      <>
        <header className="rio-hero rio-home-hero">
          <h1>Home</h1>
          {home.hello ? <p className="rio-hello">{home.hello}</p> : null}
          <HomeCredit />
        </header>
        {home.copy ? <p className="rio-note">{home.copy}</p> : null}
        <StretchLink today={home.today} />
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
            {planLine ? <p className="rio-hello-plan">{planLine}</p> : null}
            <h1 className="rio-display">{headline(season.view.days_remaining, season.inputs.goal_time)}</h1>
            {home.hello ? <p className="rio-hello">{home.hello}</p> : null}
          </div>
          <div className="rio-hero-art">
            <TrackArt />
          </div>
        </div>
        <div className="rio-stat-row rio-stat-words">
          <Stat label="Phase" value={phaseText(season.view.phase)} />
          <Stat label="Last timed effort" value={markText(season.view.mark)} />
          <Stat label="This week" value={season.view.focus || "—"} />
          <Stat label="Progress" value={season.pace_status || "No runs yet"} />
        </div>
        <div className="rio-glossary rio-soft-card">
          <Disclosure title="Details">
            <p>A training block is one phase of the season.</p>
            <p>A timed effort is a run you logged.</p>
            <p>Times use minutes:seconds.tenths, like 2:05.0.</p>
          </Disclosure>
        </div>
        <HomeCredit />
      </header>
      {season.notes.map((item) => (
        <Insight key={item.date} date={item.date} note={item.note} onDone={reload} />
      ))}
      <div className="rio-home-pair">
      {showedPhase && season.phase ? (
        <section className="rio-home-phase">
          <p className="rio-index rio-index-pad">01  /  Current phase</p>
          <Expander className="rio-phase-details" title={season.phase.collapsed}>
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
          </Expander>
        </section>
      ) : null}
      <section className="rio-home-today">
        <p className="rio-index">{workoutIndex}</p>
        {season.next ? (
          <>
            <Link className="rio-hit" href={`/session?date=${season.next.date || ""}`} onPointerDown={shareHero}>
              <WorkoutFacts
                card={season.next}
                title={todayWorkout ? "Today's workout" : "Next workout"}
                showId={home.athlete.prefs.show_ids === true}
              />
            </Link>
            {season.logging === "done" ? (
              <Watchless
                card={season.next}
                confirmAdapt={home.athlete.prefs.confirm_adapt === true}
                readOnly={readOnly}
                onSaved={reload}
              />
            ) : null}
          </>
        ) : (
          <p className="rio-empty">No workout left in this plan.</p>
        )}
        <StretchLink today={home.today} />
      </section>
      </div>
      <div className="rio-home-tail">
        <p className="rio-index rio-index-pad">{upcomingIndex}</p>
        <div className="rio-next3">
          {(season.next_days || []).map((day) => (
            <DayCard key={day.date} card={day} />
          ))}
        </div>
        {!showedPhase ? <p className="rio-index rio-index-pad">03  /  Open</p> : null}
        <div className="rio-quick">
          <Link href="/plan">Plan</Link>
          <Link href="/activity">Activity</Link>
          <Link href="/library">Library</Link>
          <Link href="/more">More</Link>
        </div>
        <Extras today={home.today} activities={season.activities} />
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
  const work = card.template_id ? card.label || "—" : "Rest day";
  const body = (
    <div className={`rio-mini ${edgeClass(work)}`}>
      <div className="rio-mini-dow">{card.day_of_week || "—"}</div>
      <div className="rio-mini-date">{card.shown_date || card.date}</div>
      <div className="rio-mini-work">{work}</div>
      {card.prescription?.line ? <p className="rio-pace-line">{card.prescription.line}</p> : null}
      {card.prescription?.tolerance ? <p className="rio-pace-range">Target range {card.prescription.tolerance}</p> : null}
      {card.prescription?.block ? <p className="rio-pace-block">Block {card.prescription.block}</p> : null}
      <HeartPace heart={card.prescription?.heart} compact />
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
        <Expander title="Carry forward">
          <p>{note.carry_forward}</p>
        </Expander>
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
      {error ? <ErrorText>{error}</ErrorText> : null}
    </section>
  );
}

function Extras({
  today,
  activities,
}: {
  today: string;
  activities?: { date?: string; name?: string; id?: string; matched?: boolean }[];
}) {
  const oldest = shiftDate(today, -13);
  const rows = (activities || []).filter(
    (row) => row.matched === false && typeof row.date === "string" && row.date >= oldest && row.date <= today,
  );
  if (!rows.length) return null;
  return (
    <section className="rio-extras">
      <p className="rio-mark-label">Extra sessions</p>
      {rows.map((row) => (
        <Link key={String(row.id || row.date)} className="rio-hit" href={`/session?activity=${row.id || ""}`}>
          <div className="rio-daycard">
            <div className="rio-mini-dow">{row.date ? weekday(row.date) : "Extra"}</div>
            <div className="rio-mini-date">{row.date}</div>
            <div className="rio-mini-work">{row.name || "Activity"}</div>
          </div>
        </Link>
      ))}
    </section>
  );
}

function shiftDate(iso: string, days: number): string {
  const day = new Date(`${iso}T12:00:00`);
  day.setDate(day.getDate() + days);
  return day.toISOString().slice(0, 10);
}

function weekday(iso: string): string {
  return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][
    new Date(`${iso}T12:00:00`).getDay()
  ];
}

function isHard(card: WorkoutCard): boolean {
  const day = card.day_of_week;
  const id = card.template_id || "";
  return (day === "Tuesday" || day === "Thursday") && Boolean(id) && !id.startsWith("aer_");
}

function Watchless({
  card,
  confirmAdapt,
  readOnly,
  onSaved,
}: {
  card: WorkoutCard;
  confirmAdapt: boolean;
  readOnly: boolean;
  onSaved: () => void;
}) {
  const [choice, setChoice] = useState("");
  const [time, setTime] = useState("");
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const queue = useRef(createSaveQueue<boolean>());
  const hard = isHard(card);
  const day = card.date || "";
  const saved = card.actual && card.actual.template_id === card.template_id ? card.actual : null;
  if (saved?.completed) {
    const parts = ["Completed"];
    if (saved.mark === "not_hitting") parts.push("Behind");
    if (saved.mark === "on_track") parts.push("On track");
    if (saved.mark === "smashing") parts.push("Ahead");
    if (saved.text) parts.push(saved.text);
    return <p className="rio-week-meta">{parts.join(" · ")}</p>;
  }

  function send(missed: boolean) {
    if (readOnly || previewing()) return;
    if (!missed && hard && choice !== "Behind" && choice !== "On track" && choice !== "Ahead") {
      setError("Choose behind, on target, or ahead.");
      return;
    }
    const flight = queue.current.push(missed, "once", async (flag) => {
      setError("");
      try {
        await api.watchless({ date: day, outcome: choice, time, missed: flag });
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
    if (hard && choice !== "Behind" && choice !== "On track" && choice !== "Ahead") {
      setError("Choose behind, on target, or ahead.");
      return;
    }
    if (hard && confirmAdapt && time.trim()) {
      setPending(true);
      setError("");
      return;
    }
    void send(false);
  }

  return (
    <div className="rio-watchless">
      {saved?.missed ? <p className="rio-settings-note">Saved as couldn&apos;t finish. Finished after all? Tap Done.</p> : null}
      {hard ? (
        <div className="rio-done-choices">
          {[
            ["Behind", "Behind"],
            ["On track", "On track"],
            ["Ahead", "Ahead"],
          ].map(([label, value]) => (
            <button key={value} type="button" className={choice === value ? "rio-primary" : "rio-secondary"} aria-pressed={choice === value} onClick={() => setChoice(value)}>
              {label}
            </button>
          ))}
        </div>
      ) : null}
      {hard ? <p className="rio-settings-note">Behind: slower than the target. On track: within 3%. Ahead: faster.</p> : null}
      {open ? (
        <>
          <label htmlFor="done-time">Time</label>
          <input id="done-time" placeholder="1:12.4" value={time} onChange={(event) => setTime(event.target.value)} />
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
          <p className="rio-week-meta">Confirm this workout before the plan changes.</p>
          <button type="button" className="rio-primary" onClick={() => send(false)} disabled={busy} aria-busy={busy}>
            Confirm
          </button>
          <button type="button" className="rio-secondary" onClick={() => setPending(false)}>
            Cancel
          </button>
        </div>
      ) : null}
      {error ? <ErrorText>{error}</ErrorText> : null}
    </div>
  );
}

function StravaOffer({ onDismiss }: { onDismiss: () => void }) {
  const [error, setError] = useState("");
  const [connectUrl, setConnectUrl] = useState("");

  useEffect(() => {
    void api
      .stravaStatus()
      .then((status) => {
        if (!status.configured || status.connected) return;
        return api.stravaConnect().then((body) => {
          if (body.url) setConnectUrl(body.url);
        });
      })
      .catch(() => setConnectUrl(""));
  }, []);

  return (
    <section className="rio-soft-card rio-strava-offer">
      <h2>Your plan is ready.</h2>
      <p>Connect Strava so your runs show up.</p>
      {connectUrl ? (
        <button type="button" className="rio-primary" onClick={() => window.location.assign(connectUrl)}>
          Connect Strava
        </button>
      ) : null}
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
      {error ? <ErrorText>{error}</ErrorText> : null}
    </section>
  );
}
