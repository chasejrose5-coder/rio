"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Expander } from "./Expander";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { PreviewBanner } from "./PreviewBanner";
import { RequireUser } from "./RequireUser";
import { ApiError, api, previewing } from "@/lib/api";
import {
  badgeKind,
  formatSynced,
  heartChart,
  summaryTiles,
  shownWeeks,
  syncEpoch,
  volumeChart,
  zoneName,
  type ChartLabel,
} from "@/lib/activity";
import { useAuth } from "@/lib/auth";
import { activityNotice, displayDistance, formatDate } from "@/lib/plan";
import type { ActivitiesResponse, RunCard, StravaStatus } from "@/lib/types";

type Mode = "loading" | "missing" | "bad" | "ready" | "error";

export function ActivityView() {
  return (
    <RequireUser>
      <ActivityBody />
    </RequireUser>
  );
}

function ActivityBody() {
  const { athlete } = useAuth();
  const [mode, setMode] = useState<Mode>("loading");
  const [body, setBody] = useState<ActivitiesResponse | null>(null);
  const [problem, setProblem] = useState("");
  const [stravaProblem, setStravaProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [rise, setRise] = useState(false);

  async function load(scope: "recent" | "all" | "read") {
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).get("preview") === "test") {
      window.sessionStorage.setItem("rio_test_preview", "1");
    }
    if (previewing()) {
      const next = await api.activities();
      if (typeof next.length === "number" && next.length <= 0) {
        setMode("bad");
        return;
      }
      setBody(next);
      setMode("ready");
      return;
    }
    const season = await api.currentSeason();
    if (!season) {
      setMode("missing");
      return;
    }
    const length = season.plan?.season_length_weeks;
    if (typeof length !== "number" || !Number.isInteger(length) || length <= 0) {
      setMode("bad");
      return;
    }
    let strava: StravaStatus | null = null;
    if (scope !== "read") {
      strava = await api.stravaStatus();
      if (strava.connected) {
        try {
          const outcome = await api.stravaSync(scope);
          setStravaProblem(stravaSentence(outcome.notice || ""));
        } catch (caught) {
          const message = caught instanceof ApiError ? caught.message : "Strava could not be reached.";
          setStravaProblem(stravaSentence(message) || message);
        }
      } else if (scope === "recent") {
        setStravaProblem("");
      }
    }
    const next = await api.activities();
    if (typeof next.length === "number" && next.length <= 0) {
      setMode("bad");
      return;
    }
    setBody(next);
    if (!strava?.connected && !(next.strava?.connected)) setStravaProblem("");
    setMode("ready");
  }

  useEffect(() => {
    const key = "rio-motion-page";
    if (window.sessionStorage.getItem(key) !== "activity") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRise(true);
    }
    window.sessionStorage.setItem(key, "activity");
    void load("recent").catch((caught) => fail(caught, setMode, setProblem));
  }, []);

  async function refresh() {
    setBusy(true);
    setProblem("");
    try {
      await load("all");
    } catch (caught) {
      fail(caught, setMode, setProblem);
    } finally {
      setBusy(false);
    }
  }

  const format = athlete?.prefs.date_format || "iso";
  const zone = zoneName(athlete?.prefs.timezone, typeof Intl === "undefined" ? "" : Intl.DateTimeFormat().resolvedOptions().timeZone);
  const range =
    body?.start_date && body.goal_date
      ? `${formatDate(body.start_date, format)} — ${formatDate(body.goal_date, format)}`
      : "";
  const connected = body?.strava?.connected === true;
  const noticeKind = activityNotice(body?.notice);
  const cards = body?.cards || [];
  const when = syncEpoch(body?.strava?.last_sync_at);
  const count = body?.strava?.count;
  const synced =
    connected && when !== null && typeof count === "number" ? `Last synced ${formatSynced(when, zone)}, ${count} runs imported` : "";

  return (
    <div className="page-activity">
      <Nav active="Activity" />
      <main className={rise ? "rio-stagger" : undefined}>
        {body?.preview?.active || previewing() ? <PreviewBanner banner={body?.preview?.banner} /> : null}
        <header className="rio-hero">
          <h1>Activity</h1>
          {mode === "ready" && range ? <p className="rio-range">{range}</p> : null}
          {problem ? <p className="rio-error">{problem}</p> : null}
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode === "missing" ? (
          <p className="rio-season-prompt">
            <Link href="/start">Generate season plan</Link>
          </p>
        ) : null}
        {mode === "bad" ? <p className="rio-empty">—</p> : null}
        {mode === "ready" && body ? (
          <>
            {connected ? (
              <section className="rio-refresh">
                <p className="rio-mark-label">Refresh from Strava</p>
                <p className="rio-note">Pulls the latest runs.</p>
                <button type="button" className="rio-secondary" disabled={busy} onClick={() => void refresh()}>
                  Refresh
                </button>
              </section>
            ) : (
              <section className="rio-refresh">
                <p className="rio-note">
                  <strong>No runs yet.</strong> Connect Strava and your runs will show up here, matched to your plan.
                </p>
                <p className="rio-strava-settings">
                  <Link href="/settings">Connect Strava in Settings</Link>
                </p>
              </section>
            )}
            {noticeKind === "missing" ? <StravaCard /> : null}
            {noticeKind === "failed" ? (
              <div className="rio-card rio-card-tight">
                <p className="rio-note">Runs could not be loaded. Try Refresh in a moment.</p>
              </div>
            ) : null}
            {stravaProblem ? <p className="rio-error">{stravaProblem}</p> : null}
            {body.preview?.status ? <p className="rio-note">{body.preview.status}</p> : null}
            {synced && !body.preview?.active ? <p className="rio-note">{synced}</p> : null}
            {cards.length ? (
              <>
                <div className="rio-stat-row rio-activity-stats">
                  <div className="rio-stat-tile">
                    <p className="rio-mark-label">Completed work</p>
                    <p className="rio-stat-value">{body.figures?.distance || "—"}</p>
                  </div>
                  <div className="rio-stat-tile">
                    <p className="rio-mark-label">Latest heart rate</p>
                    <p className="rio-stat-value">{body.figures?.heart || "—"}</p>
                  </div>
                </div>
                <section className="rio-week-summary">
                  <p className="rio-mark-label">This week</p>
                  <p className="rio-run-date">{body.summary?.title || "This week"}</p>
                  <div className="rio-summary-row">
                    {summaryTiles(body.summary).map((tile) => (
                      <div className="rio-summary-tile" key={tile.label}>
                        <p className="rio-summary-kicker">{tile.label}</p>
                        <p className="rio-summary-value">{tile.value}</p>
                      </div>
                    ))}
                  </div>
                </section>
                <Volume
                  meters={body.weekly_meters || []}
                  units={unitsOf(athlete?.prefs.units)}
                  start={body.start_date || ""}
                  length={body.length || 0}
                  today={athlete?.today || body.start_date || ""}
                />
                <Heart points={body.heart || []} />
              </>
            ) : connected ? (
              <div className="rio-card rio-card-tight">
                <p className="rio-mark-label">No runs yet</p>
                <p className="rio-note">Refresh from Strava. This week&apos;s runs, distance, and heart rate will show up here.</p>
              </div>
            ) : null}
            {(body.groups || []).map((group) => (
              <Week key={group.title} title={group.title} open={group.open} cards={group.cards} />
            ))}
            <Legacy body={body} units={unitsOf(athlete?.prefs.units)} showIds={athlete?.prefs.show_ids === true} />
          </>
        ) : null}
        <Footer />
      </main>
    </div>
  );
}

function unitsOf(value: unknown): string {
  return value === "km" ? "km" : "miles";
}

function Week({ title, open, cards }: { title: string; open: boolean; cards: RunCard[] }) {
  const [shown, setShown] = useState(open);
  return (
    <Expander className="rio-week" title={title} open={shown} onToggle={(event) => setShown(event.currentTarget.open)}>
      {cards.length ? cards.map((card) => <Run key={`${card.date}-${card.id}`} card={card} />) : <p className="rio-empty">No runs this week.</p>}
    </Expander>
  );
}

function fail(caught: unknown, setMode: (mode: Mode) => void, setProblem: (text: string) => void) {
  if (caught instanceof ApiError && caught.status === 404) {
    setMode("missing");
    return;
  }
  if (caught instanceof ApiError && caught.status === 400 && /no dates/i.test(caught.message)) {
    setMode("bad");
    return;
  }
  setProblem(caught instanceof ApiError ? caught.message : "Runs could not be loaded. Try Refresh in a moment.");
  setMode("error");
}

function stravaSentence(notice: string | null | undefined): string {
  const text = (notice || "").trim();
  if (!text || !text.startsWith("Strava")) return "";
  return text;
}

function StravaCard() {
  return (
    <div className="rio-card rio-card-tight">
      <p className="rio-mark-label">Strava isn&apos;t connected</p>
      <p className="rio-note">Connect Strava in Settings to see your runs here.</p>
      <p className="rio-strava-settings">
        <Link href="/settings">Open Settings</Link>
      </p>
    </div>
  );
}

function Run({ card }: { card: RunCard }) {
  let detail = card.detail || "—";
  if (card.laps?.length && detail.includes(" · Actual ")) detail = detail.split(" · Actual ")[0];
  return (
    <article className="rio-run">
      <header className="rio-run-head">
        <div>
          <h3 className="rio-run-name">{card.name || "Run"}</h3>
          <p className="rio-run-date">{card.shown_date}</p>
        </div>
        <span className={`rio-badge rio-badge-${badgeKind(card.status)}`}>{card.status || "Extra"}</span>
      </header>
      <p className="rio-run-detail">{detail}</p>
      {card.laps?.length ? (
        <table className="rio-laps">
          <thead>
            <tr>
              <th>Rep</th>
              <th>Target</th>
              <th>Actual</th>
              <th>Rest</th>
            </tr>
          </thead>
          <tbody>
            {card.laps.map((lap, index) => (
              <tr key={`${card.id}-${index}`}>
                <td>{lap.rep || "—"}</td>
                <td>{lap.target || "—"}</td>
                <td>{lap.actual || "—"}</td>
                <td>{lap.rest || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {card.template_id ? (
        <span hidden className="rio-template-id">
          {card.template_id}
        </span>
      ) : null}
    </article>
  );
}

function Volume({
  meters,
  units,
  start,
  length,
  today,
}: {
  meters: number[];
  units: string;
  start: string;
  length: number;
  today: string;
}) {
  const shown = shownWeeks(meters, start, length, today);
  const captions = shown.values.map((value) => displayDistance(`${value.toLocaleString("en-US")} m`, units));
  const chart = volumeChart(shown.values, units, captions, shown.highlight);
  if (!chart) return null;
  return (
    <div className="rio-volume">
      <p className="rio-mark-label">Volume · {chart.unit}</p>
      <svg className="rio-volume-line" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Weekly completed distance">
        <title>Weekly completed distance</title>
        {chart.guides.map((guide) => (
          <line key={guide.y} x1={42} y1={guide.y} x2={chart.width - 12} y2={guide.y} stroke="#DADADA" strokeWidth="1" />
        ))}
        {chart.alone ? <circle cx={chart.alone.x} cy={chart.alone.y} r="2.6" fill="#e25a32" /> : null}
        {chart.line ? <polyline points={chart.line} fill="none" stroke="#B5B5B5" strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" /> : null}
        {chart.highlight ? <circle cx={chart.highlight.x} cy={chart.highlight.y} r="3.6" fill="#e25a32" /> : null}
        {chart.yLabels.map((label) => (
          <text key={`y-${label.text}-${label.y}`} x={label.x} y={label.y} textAnchor="end" dominantBaseline="middle" fill="#6B6B6B" fontSize="10">
            {label.text}
          </text>
        ))}
        {chart.xLabels.map((label) => (
          <AxisText key={`x-${label.text}-${label.x}`} label={label} />
        ))}
        {chart.tips.map((tip, index) => (
          <circle key={`tip-${index}`} cx={tip.x} cy={tip.y} r="8" fill="transparent">
            <title>{tip.text}</title>
          </circle>
        ))}
      </svg>
    </div>
  );
}

function Heart({ points }: { points: { date: string; bpm: number }[] }) {
  const chart = heartChart(points);
  if (!chart) return null;
  return (
    <div className="rio-heart rio-heart-axis">
      <p className="rio-mark-label">Heart rate · bpm</p>
      <svg className="rio-heart-axis-line" viewBox={`0 0 ${chart.width} ${chart.height}`} role="img" aria-label="Average heart rate">
        <title>Average heart rate</title>
        <line x1={chart.left} y1={chart.top} x2={chart.left} y2={chart.plotBottom} stroke="#6B6B6B" strokeWidth="1.25" />
        <line x1={chart.left} y1={chart.plotBottom} x2={chart.right} y2={chart.plotBottom} stroke="#DADADA" strokeWidth="1" />
        {chart.ticks.map((tick, index) => (
          <g key={`${tick.text}-${index}`}>
            <line x1={chart.left} y1={tick.y} x2={chart.right} y2={tick.y} stroke="#E4E4E4" strokeWidth="1" />
            <text x={chart.left - 8} y={tick.y} textAnchor="end" dominantBaseline="middle" fill="#6B6B6B" fontSize="11">
              {tick.text}
            </text>
          </g>
        ))}
        {chart.dots.map((dot, index) => (
          <circle key={`${dot.date}-${dot.bpm}-${index}`} cx={dot.x} cy={dot.y} r="4.5" fill="#E25A32">
            <title>
              {dot.date} · {Math.round(dot.bpm)} bpm
            </title>
          </circle>
        ))}
        {chart.dates.map((label, index) => (
          <text key={`${label.text}-${label.x}-${index}`} x={label.x} y={label.y} textAnchor="middle" fill="#6B6B6B" fontSize="11">
            {label.text}
          </text>
        ))}
      </svg>
    </div>
  );
}

function AxisText({ label }: { label: ChartLabel }) {
  return (
    <text x={label.x} y={label.y} textAnchor={label.anchor} fill="#6B6B6B" fontSize="10">
      {label.text}
    </text>
  );
}

function Legacy({ body, units, showIds }: { body: ActivitiesResponse; units: string; showIds: boolean }) {
  const rows = body.rows || [];
  const all = body.all || [];
  return (
    <div hidden className="rio-legacy-activity">
      {rows.length ? null : <p className="rio-empty">No matched activities.</p>}
      {rows.length ? (
        <>
          <p className="rio-mark-label">Sessions</p>
          <table className="rio-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Workout</th>
                <th>Work</th>
                <th>Avg HR</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => {
                let label = row.label || "—";
                if (showIds && row.template_id && !label.includes(row.template_id)) label = `${label} · ${row.template_id}`;
                const work = row.meters != null ? displayDistance(row.work || "—", units) || row.work || "—" : row.work || "—";
                return (
                  <tr key={`${row.date}-${index}`}>
                    <td>{row.shown_date || "—"}</td>
                    <td>{label}</td>
                    <td>{work}</td>
                    <td>{row.hr || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      ) : null}
      {all.length ? (
        <>
          <p className="rio-mark-label">All activities</p>
          <table className="rio-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Activity</th>
                <th>Distance</th>
                <th>Avg HR</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {all.map((row, index) => (
                <tr key={`${row.id || row.date}-${index}`}>
                  <td>{row.shown_date || "—"}</td>
                  <td>{row.name || "—"}</td>
                  <td>{row.meters != null ? displayDistance(String(row.distance || row.work || "—"), units) || "—" : "—"}</td>
                  <td>{row.hr || "—"}</td>
                  <td>{row.extra ? "extra" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
    </div>
  );
}
