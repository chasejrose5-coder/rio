"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isPastSeason, planQuery, rowLabel, rowValues, seasonKey, seasonRows, unreadableMessage } from "@/lib/past";
import type { StoredSeason } from "@/lib/types";

const DELETE_NOTE = "This permanently deletes this season and the workouts stored with it. It can't be undone.";

export function PastSeasonsView() {
  return (
    <RequireUser>
      <PastSeasonsBody />
    </RequireUser>
  );
}

function PastSeasonsBody() {
  const { athlete } = useAuth();
  const [rows, setRows] = useState<StoredSeason[] | null>(null);
  const [today, setToday] = useState("");
  const [problem, setProblem] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [busy, setBusy] = useState(false);
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);

  const dateFormat = athlete?.prefs.date_format === "iso" ? "iso" : "short";
  const compact = athlete?.prefs.compact === true;

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "past-seasons";
    window.sessionStorage.setItem(key, "past-seasons");
    if (first) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setArm(true);
    }
  }, []);

  useEffect(() => {
    if (!arm || rows === null) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRise(true);
    const timer = window.setTimeout(() => setRise(false), 280);
    return () => window.clearTimeout(timer);
  }, [arm, rows]);

  useEffect(() => {
    let live = true;
    api
      .pastSeasons()
      .then((body) => {
        if (!live) return;
        setToday(body.today);
        setRows(seasonRows(body.seasons, body.open));
        setProblem("");
      })
      .catch((caught) => {
        if (!live) return;
        const message = caught instanceof ApiError ? caught.message : "This account's seasons could not be read.";
        setRows(null);
        setProblem(unreadableMessage(message) || message);
      });
    return () => {
      live = false;
    };
  }, []);

  async function remove(row: StoredSeason) {
    setBusy(true);
    setConfirmError("");
    try {
      await api.deletePastSeason({ ...row.inputs, confirm: true });
      setRows((current) => (current || []).filter((item) => seasonKey(item.inputs) !== seasonKey(row.inputs)));
      setPending("");
      setNotice("Season deleted.");
    } catch (caught) {
      setConfirmError(caught instanceof ApiError ? caught.message : "That season could not be deleted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={compact ? "page-past is-compact" : "page-past"}>
      <Nav active="More" />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>Past seasons</h1>
        </header>
        {notice ? <p className="rio-past-deleted">{notice}</p> : null}
        {problem ? <p className="rio-error">{problem}</p> : null}
        {rows === null && !problem ? <p className="rio-wait">Loading</p> : null}
        {rows && rows.length === 0 ? <p className="rio-empty">No seasons on this account.</p> : null}
        {rows && rows.length > 0 ? (
          <div className="rio-past-list">
            {rows.map((row) => {
              const key = seasonKey(row.inputs);
              const shown = rowValues(row.inputs, dateFormat);
              const past = isPastSeason(row.inputs.goal_date, today);
              const open = pending === key;
              return (
                <section className="rio-past-item" key={key}>
                  <Link className="rio-past-row" href={planQuery(row.inputs)} aria-label={rowLabel(row.inputs, dateFormat)}>
                    <span className="rio-past-cell">
                      <span className="rio-past-k">Start date</span>
                      <span className="rio-past-v">{shown.start}</span>
                    </span>
                    <span className="rio-past-cell">
                      <span className="rio-past-k">Goal date</span>
                      <span className="rio-past-v">{shown.goal}</span>
                    </span>
                    <span className="rio-past-cell rio-past-time">
                      <span className="rio-past-k">Goal time</span>
                      <span className="rio-past-v">{shown.time}</span>
                    </span>
                  </Link>
                  {past ? (
                    <button
                      type="button"
                      className="rio-past-delete"
                      onClick={() => {
                        setPending(key);
                        setConfirmError("");
                        setNotice("");
                      }}
                    >
                      Delete season
                    </button>
                  ) : null}
                  {past && open ? (
                    <div className="rio-past-confirm">
                      <p className="rio-past-confirm-title">Delete this season?</p>
                      {row.stats.map((stat) => (
                        <div className="rio-past-stat" key={stat.label}>
                          <div className="rio-past-k">{stat.label}</div>
                          <div className="rio-past-v">{stat.value}</div>
                        </div>
                      ))}
                      <p className="rio-past-confirm-note">{DELETE_NOTE}</p>
                      {confirmError ? <p className="rio-error">{confirmError}</p> : null}
                      <div className="rio-done-row rio-past-actions">
                        <button type="button" className="rio-primary" disabled={busy} onClick={() => void remove(row)}>
                          Delete permanently
                        </button>
                        <button
                          type="button"
                          className="rio-secondary"
                          disabled={busy}
                          onClick={() => {
                            setPending("");
                            setConfirmError("");
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : null}
                </section>
              );
            })}
          </div>
        ) : null}
        <Footer />
      </main>
    </div>
  );
}
