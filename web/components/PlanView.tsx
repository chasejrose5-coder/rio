"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Expander } from "./Expander";
import { Footer, PhotoCredit } from "./Footer";
import { Nav } from "./Nav";
import { PreviewBanner } from "./PreviewBanner";
import { RequireUser } from "./RequireUser";
import { ApiError, api, previewing } from "@/lib/api";
import {
  PLAN_VIEWS,
  activityNotice,
  addDays,
  daysLabel,
  displayDistance,
  distancesFromRows,
  extrasBetween,
  formatDate,
  isPlanView,
  lengthText,
  linkError,
  markLabel,
  monthKey,
  monthTitle,
  paceStatusLine,
  plainReasonLines,
  recapView,
  statusLabel,
  volumeLabel,
  weekContaining,
  weekOption,
  weekSpan,
  weekSunday,
  weekdayName,
  type PlanViewName,
} from "@/lib/plan";
import type { ActivitiesResponse, CurrentSeason, PlanDay, PlanResponse, PlanSession } from "@/lib/types";

const VIEW_KEY = "rio_plan_last";

function namedSeason(params: URLSearchParams) {
  const current_time = params.get("current_time") || "";
  const start_date = params.get("start_date") || "";
  const goal_time = params.get("goal_time") || "";
  const goal_date = params.get("goal_date") || "";
  if (!current_time || !start_date || !goal_time || !goal_date) return undefined;
  return { current_time, start_date, goal_time, goal_date };
}
const CAL_DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MARK_CHOICES = [
  ["on_track", "On track"],
  ["not_hitting", "Not hitting"],
  ["smashing", "Smashing"],
] as const;

type Mode = "loading" | "ready" | "missing" | "bad" | "error";
type Pending = { week: number; choice: string };

export function PlanView() {
  return (
    <RequireUser>
      <PlanBody />
    </RequireUser>
  );
}

function PlanBody() {
  const [mode, setMode] = useState<Mode>("loading");
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [season, setSeason] = useState<CurrentSeason | null>(null);
  const [activities, setActivities] = useState<ActivitiesResponse | null>(null);
  const [pace, setPace] = useState("No runs yet");
  const [problem, setProblem] = useState("");
  const [activityNote, setActivityNote] = useState("");
  const [view, setView] = useState<PlanViewName>("Calendar");
  const [rise, setRise] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [markError, setMarkError] = useState("");

  async function load(month?: string) {
    const params = typeof window === "undefined" ? new URLSearchParams() : new URLSearchParams(window.location.search);
    if (params.get("preview") === "test") window.sessionStorage.setItem("rio_test_preview", "1");
    const link = linkError(params);
    const named = previewing() ? undefined : namedSeason(params);
    try {
      const [planBody, homeBody, seasonBody] = await Promise.all([
        api.plan(month, named),
        api.home(false),
        previewing() ? Promise.resolve(null) : api.currentSeason(),
      ]);
      let activityBody: ActivitiesResponse | null = null;
      setActivityNote("");
      try {
        activityBody = await api.activities();
      } catch (caught) {
        if (!(caught instanceof ApiError && caught.status === 404)) {
          setActivityNote("Runs could not be loaded. Try Refresh in a moment.");
        }
      }
      setPlan(planBody);
      setSeason(
        seasonBody || planBody.actuals
          ? {
              today: seasonBody?.today || planBody.prefs.today || "",
              inputs: planBody.inputs,
              actuals: planBody.actuals ?? seasonBody?.actuals,
              marks: planBody.marks,
              digest: planBody.digest,
            }
          : null,
      );
      setActivities(activityBody);
      setPace(planBody.pace_status || homeBody.season?.pace_status || "No runs yet");
      setProblem(link);
      setMode("ready");
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : "Plan could not be loaded.";
      if (caught instanceof ApiError && caught.status === 404) {
        setProblem(link);
        setMode("missing");
        return;
      }
      if (caught instanceof ApiError && caught.status === 400 && /no weeks|no dates/i.test(message)) {
        setProblem("");
        setMode("bad");
        return;
      }
      setProblem(message);
      setMode("error");
    }
  }

  useEffect(() => {
    const stored = window.sessionStorage.getItem(VIEW_KEY);
    if (isPlanView(stored)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setView(stored);
    }
    const motion = window.sessionStorage.getItem("rio-motion-page");
    if (motion !== "plan") setRise(true);
    window.sessionStorage.setItem("rio-motion-page", "plan");
    void load();
  }, []);

  function chooseView(next: PlanViewName) {
    setView(next);
    window.sessionStorage.setItem(VIEW_KEY, next);
  }

  async function commit(week: number, choice: string) {
    if (!plan) return;
    if (previewing()) {
      setPending(null);
      return;
    }
    setMarkError("");
    try {
      await api.markWeek(week, choice, plan.digest);
      setPending(null);
      await load(plan.month);
    } catch (caught) {
      setMarkError(caught instanceof ApiError ? caught.message : "The mark could not be saved.");
    }
  }

  function chooseMark(week: number, choice: string) {
    if (plan?.prefs.confirm_adapt) {
      setPending({ week, choice });
      return;
    }
    void commit(week, choice);
  }

  const title = plan && mode === "ready" ? lengthText(plan.weeks.length) : "Plan";
  const range =
    plan && mode === "ready"
      ? `${formatDate(plan.inputs.start_date, plan.prefs.date_format || "iso")} — ${formatDate(plan.inputs.goal_date, plan.prefs.date_format || "iso")}`
      : "";

  const compact = plan?.prefs.compact === true;
  return (
    <div className={compact ? "page-plan is-compact" : "page-plan"}>
      <Nav active="Plan" />
      <main className={rise ? "rio-stagger" : undefined}>
        {plan?.preview?.active || previewing() ? <PreviewBanner banner={plan?.preview?.banner} /> : null}
        <header className="rio-plan-hero">
          <h1>{title}</h1>
          {range ? <p className="rio-range">{range}</p> : null}
          {problem ? <p className="rio-error">{problem}</p> : null}
          <PhotoCredit onPhoto>Photo by Jan van der Wolf on Pexels</PhotoCredit>
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode === "missing" && !problem ? (
          <p className="rio-season-prompt">
            <Link href="/start">Generate season plan</Link>
          </p>
        ) : null}
        {mode === "bad" ? <p className="rio-empty">—</p> : null}
        {mode === "ready" && plan ? (
          <PlanReady
            plan={plan}
            season={season}
            activities={activities}
            activityNote={activityNote}
            pace={pace}
            view={view}
            picked={picked}
            pending={pending}
            markError={markError}
            onView={chooseView}
            onMonth={(month) => void load(month)}
            onWeek={setPicked}
            onChoose={chooseMark}
            onConfirm={() => {
              if (pending) void commit(pending.week, pending.choice);
            }}
            onCancel={() => setPending(null)}
          />
        ) : null}
        <Footer />
      </main>
    </div>
  );
}

function PlanReady({
  plan,
  season,
  activities,
  activityNote,
  pace,
  view,
  picked,
  pending,
  markError,
  onView,
  onMonth,
  onWeek,
  onChoose,
  onConfirm,
  onCancel,
}: {
  plan: PlanResponse;
  season: CurrentSeason | null;
  activities: ActivitiesResponse | null;
  activityNote: string;
  pace: string;
  view: PlanViewName;
  picked: number | null;
  pending: Pending | null;
  markError: string;
  onView: (view: PlanViewName) => void;
  onMonth: (month: string) => void;
  onWeek: (week: number) => void;
  onChoose: (week: number, choice: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const format = plan.prefs.date_format || "iso";
  const showIds = plan.prefs.show_ids === true;
  const units = plan.prefs.units || "miles";
  const today = plan.prefs.today || "";
  const length = plan.weeks.length;
  const current = plan.weeks.find((row) => row.status === "current");
  const phaseNote = current && current.phase && current.phase !== "—" ? `This week is phase ${current.phase}.` : "";
  const emptyWeeks = plan.weeks.every((row) => row.meters === 0);
  const selected = picked && picked >= 1 && picked <= length ? picked : weekContaining(plan.inputs.start_date, length, today);
  const distances = distancesFromRows(activities?.rows || []);
  const recap = recapView({
    week: selected,
    sessions: plan.sessions,
    actuals: season?.actuals || {},
    marks: plan.marks || {},
    distances,
  });

  return (
    <>
      <p className="rio-note rio-after-hero">{paceStatusLine(pace)}</p>
      <section className="rio-card rio-card-tight">
        <p className="rio-mark-label">Phases</p>
        {phaseNote ? <p className="rio-note">{phaseNote}</p> : null}
        <div className="rio-phases">
          {plan.weeks.map((row) => (
            <div key={row.week} className={row.status === "current" ? "rio-phase rio-phase-now" : "rio-phase"}>
              <div className="rio-phase-week">W{row.week}</div>
              <div className="rio-phase-num">{row.phase}</div>
            </div>
          ))}
        </div>
      </section>
      <fieldset className="rio-segments">
        <legend className="rio-sr">Plan view</legend>
        {PLAN_VIEWS.map((name) => (
          <label key={name} className={view === name ? "is-selected" : undefined}>
            <input type="radio" name="plan-view" value={name} checked={view === name} onChange={() => onView(name)} />
            {name}
          </label>
        ))}
      </fieldset>
      <div className="rio-plan-gap" />
      <Expander className="rio-weeks" title="Weeks">
        {emptyWeeks ? (
          <p className="rio-note">No runs logged yet. A week shows distance after a workout is saved.</p>
        ) : null}
        <div className="rio-progress-list">
          {plan.weeks.map((row) => (
            <div key={row.week} className={`rio-progress rio-progress-${row.status || "open"}`}>
              <span className="rio-progress-tick" />
              <div className="rio-progress-week">Week {row.week}</div>
              <div className="rio-progress-phase">
                Phase {row.phase}
                <div className="rio-progress-volume">{volumeLabel(row.meters, row.volume, units)}</div>
              </div>
              <div className="rio-progress-status">{row.status || "—"}</div>
              <div className="rio-progress-days">{daysLabel(row.days_remaining)}</div>
            </div>
          ))}
        </div>
      </Expander>
      <div key={view} className="rio-plan-view">
        {view === "Calendar" ? <Calendar plan={plan} onMonth={onMonth} /> : null}
        {view === "This week" ? (
          <ThisWeek
            plan={plan}
            week={selected}
            format={format}
            recap={recap}
            units={units}
            activities={activities}
            activityNote={activityNote}
            showIds={showIds}
            pending={pending}
            markError={markError}
            onWeek={onWeek}
            onChoose={onChoose}
            onConfirm={onConfirm}
            onCancel={onCancel}
          />
        ) : null}
        {view === "Full season" ? (
          <FullSeason
            plan={plan}
            format={format}
            showIds={showIds}
            pending={pending}
            markError={markError}
            onChoose={onChoose}
            onConfirm={onConfirm}
            onCancel={onCancel}
          />
        ) : null}
      </div>
    </>
  );
}

function Calendar({ plan, onMonth }: { plan: PlanResponse; onMonth: (month: string) => void }) {
  return (
    <section>
      <h2 className="rio-section">{plan.month_title}</h2>
      <div className="rio-pick">
        <label htmlFor="plan-month">Month</label>
        <select
          id="plan-month"
          value={plan.month}
          onChange={(event) => onMonth(event.target.value)}
        >
          {plan.months.map((iso) => (
            <option key={iso} value={monthKey(iso)}>
              {monthTitle(iso)}
            </option>
          ))}
        </select>
      </div>
      <div className="rio-cal">
        {CAL_DOW.map((name) => (
          <div key={name} className="rio-cal-dow">
            {name}
          </div>
        ))}
        {plan.calendar.flat().map((cell) => (
          <CalCell key={cell.date} cell={cell} />
        ))}
      </div>
    </section>
  );
}

function CalCell({ cell }: { cell: PlanDay }) {
  const classes = ["rio-cal-day"];
  if (!cell.in_month) classes.push("rio-cal-out");
  else if (cell.template_id) classes.push("rio-cal-session");
  else classes.push("rio-cal-quiet");
  if (cell.today && cell.in_month) classes.push("rio-cal-today");
  const body = (
    <>
      <div className="rio-cal-num">{cell.in_month ? cell.day : ""}</div>
      <div className="rio-cal-label">{cell.in_month ? cell.label : ""}</div>
    </>
  );
  if (!cell.in_month || !cell.template_id) {
    return (
      <div className={classes.join(" ")} data-date={cell.in_month ? cell.date : undefined}>
        {body}
      </div>
    );
  }
  return (
    <Link
      className={classes.join(" ")}
      href={`/session?date=${cell.date}`}
      aria-label={`${cell.date}. ${cell.label || "Session"}`}
      data-date={cell.date}
      data-today={cell.today ? "true" : "false"}
    >
      {body}
    </Link>
  );
}

function ThisWeek({
  plan,
  week,
  format,
  recap,
  units,
  activities,
  activityNote,
  showIds,
  pending,
  markError,
  onWeek,
  onChoose,
  onConfirm,
  onCancel,
}: {
  plan: PlanResponse;
  week: number;
  format: string;
  recap: { completed: string; marks: string; volume: string; next: string };
  units: string;
  activities: ActivitiesResponse | null;
  activityNote: string;
  showIds: boolean;
  pending: Pending | null;
  markError: string;
  onWeek: (week: number) => void;
  onChoose: (week: number, choice: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const days = daysFor(plan, week);
  const phase = phaseOf(plan, week);
  const sunday = weekSunday(plan.inputs.start_date, week);
  const extras = extrasBetween(activities?.all || [], sunday, addDays(sunday, 6));
  const applied = plan.marks[String(week)];
  return (
    <section className="rio-this-week">
      <header className="rio-hero rio-hero-week">
        <h2>Week {week}</h2>
        <p className="rio-range">{weekSpan(plan.inputs.start_date, week, phase, format)}</p>
      </header>
      <div className="rio-pick">
        <label htmlFor="plan-week">Week</label>
        <select id="plan-week" value={String(week)} onChange={(event) => onWeek(Number(event.target.value))}>
          {plan.weeks.map((row) => (
            <option key={row.week} value={row.week}>
              {weekOption(plan.inputs.start_date, row.week, format)}
            </option>
          ))}
        </select>
      </div>
      <ActivityNotice notice={activities?.notice} fallback={activityNote} />
      <section className="rio-recap">
        <p className="rio-mark-label">Recap</p>
        <dl>
          <div className="rio-field">
            <dt>Sessions</dt>
            <dd>{recap.completed}</dd>
          </div>
          <div className="rio-field">
            <dt>Marks</dt>
            <dd>{recap.marks}</dd>
          </div>
          <div className="rio-field">
            <dt>Volume</dt>
            <dd>{displayDistance(recap.volume, units)}</dd>
          </div>
          <div className="rio-field">
            <dt>Next week</dt>
            <dd>{recap.next}</dd>
          </div>
        </dl>
      </section>
      {days.length === 0 ? <p className="rio-empty">—</p> : days.map((session) => (
        <DayCard key={session.date} session={session} detail={matchedDetail(activities, session.date)} showIds={showIds} />
      ))}
      {extras.length > 0 ? (
        <div className="rio-extras">
          <p className="rio-mark-label">Extra sessions</p>
          {extras.map((row) => (
            <ExtraCard key={row.id || row.date} row={row} format={format} />
          ))}
        </div>
      ) : null}
      <Marks
        week={week}
        applied={applied}
        showApplied
        pending={pending}
        markError={markError}
        onChoose={onChoose}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />
    </section>
  );
}

function FullSeason({
  plan,
  format,
  showIds,
  pending,
  markError,
  onChoose,
  onConfirm,
  onCancel,
}: {
  plan: PlanResponse;
  format: string;
  showIds: boolean;
  pending: Pending | null;
  markError: string;
  onChoose: (week: number, choice: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <section>
      <h2 className="rio-section">Full season</h2>
      {plan.weeks.map((row) => {
        const days = daysFor(plan, row.week);
        const applied = plan.marks[String(row.week)];
        return (
          <article key={row.week} className="rio-week">
            <div className="rio-week-head">
              <h3 className="rio-week-title">
                <span className="rio-week-num">Week {row.week}</span>
                <span className="rio-week-sep"> · </span>
                <span className="rio-week-phase">Phase {row.phase}</span>
              </h3>
              {applied ? <p className="rio-week-meta">{markLabel(applied)}</p> : null}
            </div>
            {days.length === 0 ? (
              <p className="rio-empty">—</p>
            ) : (
              <>
                <div className="rio-days">
                  {days.map((session, index) => (
                    <DayRow key={session.date} session={session} first={index === 0} format={format} showIds={showIds} />
                  ))}
                </div>
                <Expander className="rio-reasons-box" title="Reasons">
                  {days.map((session) => {
                    const lines = plainReasonLines(session.reason_codes);
                    return (
                      <div key={session.date}>
                        <p className="rio-reason-day">
                          {session.day_of_week} {session.shown_date || formatDate(session.date, format)}
                        </p>
                        {lines.length ? lines.map((line, index) => (
                          <p key={`${session.date}-${index}`} className="rio-reason">
                            {line}
                          </p>
                        )) : (
                          <p className="rio-empty">—</p>
                        )}
                      </div>
                    );
                  })}
                </Expander>
              </>
            )}
            <Marks
              week={row.week}
              applied={applied}
              showApplied={false}
              pending={pending}
              markError={pending?.week === row.week ? markError : ""}
              onChoose={onChoose}
              onConfirm={onConfirm}
              onCancel={onCancel}
            />
          </article>
        );
      })}
    </section>
  );
}

function DayCard({ session, detail, showIds }: { session: PlanSession; detail: string; showIds: boolean }) {
  const work = session.label || "—";
  const name = `${session.day_of_week || "Day"} ${session.date}. ${work}`;
  const templateId = (session.template_id || "").trim();
  const card = (
    <div className="rio-daycard">
      <div className="rio-daycard-dow">{session.day_of_week}</div>
      <div className="rio-daycard-date">{session.shown_date || session.date}</div>
      <div className="rio-daycard-work">{work}</div>
      {showIds && templateId ? <div className="rio-template-id rio-daycard-id">{templateId}</div> : null}
      <PaceLines session={session} />
      <div className="rio-daycard-target">{session.target || "—"}</div>
      {detail ? <div className="rio-daycard-actual">{detail}</div> : null}
    </div>
  );
  if (!session.template_id || !session.date) return card;
  return (
    <Link className="rio-hit" href={`/session?date=${session.date}`} aria-label={name}>
      {card}
    </Link>
  );
}

function DayRow({
  session,
  first,
  format,
  showIds,
}: {
  session: PlanSession;
  first: boolean;
  format: string;
  showIds: boolean;
}) {
  const work = session.label || "—";
  const status = statusLabel(session.reason_codes);
  const name = `${session.day_of_week || "Day"} ${session.date}. ${work}`;
  const templateId = (session.template_id || "").trim();
  const row = (
    <div className={first ? "rio-day" : "rio-day rio-day-next"}>
      <div className="rio-when">
        <div className="rio-dow">{session.day_of_week}</div>
        <div className="rio-date">{session.shown_date || formatDate(session.date, format)}</div>
      </div>
      <div className="rio-work">
        <div className="rio-name">{work}</div>
        {showIds && templateId ? <div className="rio-template-id">{templateId}</div> : null}
        <PaceLines session={session} />
        <div className="rio-target">{session.target || "—"}</div>
      </div>
      {status ? <div className="rio-status">{status}</div> : null}
    </div>
  );
  if (!session.template_id || !session.date) return row;
  return (
    <Link className="rio-hit" href={`/session?date=${session.date}`} aria-label={name}>
      {row}
    </Link>
  );
}

function ExtraCard({
  row,
  format,
}: {
  row: { date?: string; name?: string; id?: string; shown_date?: string };
  format: string;
}) {
  const day = row.date || "";
  const name = (row.name || "").trim() || "Activity";
  const weekday = weekdayName(day) || "Extra";
  const card = (
    <div className="rio-daycard">
      <div className="rio-daycard-dow">{weekday}</div>
      <div className="rio-daycard-date">{row.shown_date || formatDate(day, format)}</div>
      <div className="rio-daycard-work">{name}</div>
    </div>
  );
  if (!row.id) return card;
  return (
    <Link className="rio-hit" href={`/session?activity=${encodeURIComponent(row.id)}`} aria-label={`${weekday} ${day}. ${name}`}>
      {card}
    </Link>
  );
}

function PaceLines({ session }: { session: PlanSession }) {
  const prescription = session.prescription;
  if (!prescription?.line && !prescription?.tolerance && !prescription?.block) return null;
  return (
    <div className="rio-pace">
      {prescription.line ? <p className="rio-pace-line">{prescription.line}</p> : null}
      {prescription.tolerance ? <p className="rio-pace-range">Tolerance {prescription.tolerance}</p> : null}
      {prescription.block ? <p className="rio-pace-block">Block {prescription.block}</p> : null}
    </div>
  );
}

function Marks({
  week,
  applied,
  showApplied,
  pending,
  markError,
  onChoose,
  onConfirm,
  onCancel,
}: {
  week: number;
  applied: string | undefined;
  showApplied: boolean;
  pending: Pending | null;
  markError: string;
  onChoose: (week: number, choice: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const asking = pending?.week === week ? pending : null;
  return (
    <div className="rio-week-mark">
      {showApplied && applied ? <p className="rio-week-meta">{markLabel(applied)}</p> : null}
      <p className="rio-mark-label">Mark</p>
      <div className="rio-marks">
        {MARK_CHOICES.map(([choice, label]) => (
          <button
            key={choice}
            type="button"
            className={applied === choice ? "rio-primary" : "rio-secondary"}
            aria-pressed={applied === choice}
            onClick={() => onChoose(week, choice)}
          >
            {label}
          </button>
        ))}
      </div>
      {asking ? (
        <div className="rio-confirm">
          <p className="rio-week-meta">Confirm {markLabel(asking.choice)} before the plan changes.</p>
          <button type="button" className="rio-primary" onClick={onConfirm}>
            Confirm
          </button>
          <button type="button" className="rio-secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      ) : null}
      {markError ? <p className="rio-error">{markError}</p> : null}
    </div>
  );
}

function ActivityNotice({ notice, fallback }: { notice: string | null | undefined; fallback: string }) {
  const kind = activityNotice(notice);
  if (kind === "missing") {
    return (
      <div className="rio-card rio-card-tight">
        <p className="rio-mark-label">{"Strava isn't connected"}</p>
        <p className="rio-note">Connect Strava in Settings to see your runs here.</p>
        <p className="rio-season-prompt">
          <Link href="/settings">Open Settings</Link>
        </p>
      </div>
    );
  }
  if (kind === "failed" || fallback) {
    return (
      <div className="rio-card rio-card-tight">
        <p className="rio-note">Runs could not be loaded. Try Refresh in a moment.</p>
      </div>
    );
  }
  return null;
}

function daysFor(plan: PlanResponse, week: number): PlanSession[] {
  return plan.sessions
    .filter((session) => session.week_number === week)
    .slice()
    .sort((a, b) => a.date.localeCompare(b.date));
}

function phaseOf(plan: PlanResponse, week: number): string {
  return plan.weeks.find((row) => row.week === week)?.phase || "—";
}

function matchedDetail(activities: ActivitiesResponse | null, date: string): string {
  const row = activities?.rows.find((item) => item.date === date);
  if (!row) return "";
  const parts: string[] = [];
  if (row.work && row.work !== "—") parts.push(row.work);
  if (row.hr && row.hr !== "—") parts.push(row.hr);
  return parts.join(" · ");
}
