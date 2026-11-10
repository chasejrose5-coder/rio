"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  GOAL_ERROR,
  PACE_ERROR,
  canonicalEasyPace,
  cleanGoal,
  savedPaceLine,
  shownField,
} from "@/lib/profile";
import type { ProfileResponse } from "@/lib/types";

type Mode = "loading" | "ready" | "error";

export function ProfileView() {
  return (
    <RequireUser>
      <ProfileBody />
    </RequireUser>
  );
}

function ProfileBody() {
  const { athlete, refresh } = useAuth();
  const [mode, setMode] = useState<Mode>("loading");
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [problem, setProblem] = useState("");
  const [pace, setPace] = useState("");
  const [unit, setUnit] = useState<"mi" | "km">("mi");
  const [paceError, setPaceError] = useState("");
  const [paceBusy, setPaceBusy] = useState(false);
  const [goal, setGoal] = useState("");
  const [goalError, setGoalError] = useState("");
  const [goalBusy, setGoalBusy] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "profile";
    window.sessionStorage.setItem(key, "profile");
    if (first) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setArm(true);
    }
  }, []);

  useEffect(() => {
    if (!arm || mode === "loading") return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRise(true);
    const timer = window.setTimeout(() => setRise(false), 280);
    return () => window.clearTimeout(timer);
  }, [arm, mode]);

  useEffect(() => {
    let live = true;
    api
      .profile()
      .then((body) => {
        if (!live) return;
        setProfile(body);
        setProblem("");
        setMode("ready");
      })
      .catch((caught) => {
        if (!live) return;
        setProfile(null);
        setProblem(caught instanceof ApiError ? caught.message : "This account could not be opened.");
        setMode("error");
      });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (seeded) return;
    const source = profile ?? null;
    const fromAthlete = !source && mode === "error";
    if (!source && !fromAthlete) return;
    const nextPace = source?.easy_pace || String(athlete?.prefs.easy_pace || "");
    const nextUnit = source?.easy_pace_unit || String(athlete?.prefs.easy_pace_unit || "mi");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPace(nextPace);
    setUnit(nextUnit === "km" ? "km" : "mi");
    if (source?.ready) setGoal(source.shown_goal && source.shown_goal !== "—" ? source.shown_goal : "");
    setSeeded(true);
  }, [profile, athlete, mode, seeded]);

  const dateFormat = String(profile?.prefs?.date_format || athlete?.prefs.date_format || "iso");
  const compact = profile?.prefs?.compact === true || athlete?.prefs.compact === true;
  const phrase = profile?.easy_pace_phrase || "";
  const fields = profile?.fields ?? [];
  const starting = fields.filter((field) => field.label === "Current 800 time" || field.label === "Start date");
  const goalDate = fields.filter((field) => field.label === "Goal date");
  const failed = mode === "error";

  async function savePace(event: React.FormEvent) {
    event.preventDefault();
    const cleaned = canonicalEasyPace(pace);
    if (!cleaned) {
      setPaceError(PACE_ERROR);
      return;
    }
    setPaceBusy(true);
    setPaceError("");
    try {
      const saved = await api.patchSettings({ easy_pace: cleaned, easy_pace_unit: unit });
      const nextPhrase = String(saved.prefs.easy_pace_phrase || "");
      setPace(String(saved.prefs.easy_pace || cleaned));
      setUnit(saved.prefs.easy_pace_unit === "km" ? "km" : "mi");
      setProfile((current) =>
        current
          ? {
              ...current,
              easy_pace: String(saved.prefs.easy_pace || cleaned),
              easy_pace_unit: saved.prefs.easy_pace_unit === "km" ? "km" : "mi",
              easy_pace_phrase: nextPhrase,
            }
          : current,
      );
      await refresh();
    } catch (caught) {
      setPaceError(caught instanceof ApiError ? caught.message : "Easy pace could not be saved.");
    } finally {
      setPaceBusy(false);
    }
  }

  async function saveGoal(event: React.FormEvent) {
    event.preventDefault();
    const cleaned = cleanGoal(goal);
    if (!cleaned) {
      setGoalError(GOAL_ERROR);
      return;
    }
    setGoalBusy(true);
    setGoalError("");
    try {
      const saved = await api.saveGoal(cleaned);
      setProfile(saved);
      setGoal(saved.shown_goal && saved.shown_goal !== "—" ? saved.shown_goal : cleaned);
    } catch (caught) {
      setGoalError(caught instanceof ApiError ? caught.message : GOAL_ERROR);
    } finally {
      setGoalBusy(false);
    }
  }

  return (
    <div className={compact ? "page-profile is-compact" : "page-profile"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>Profile</h1>
          {failed ? <p className="rio-error">{problem}</p> : null}
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode !== "loading" ? (
          <>
            <section className="rio-easy">
              <p className="rio-easy-kicker">Start here</p>
              <h1>Your easy pace</h1>
              <p className="rio-easy-body">
                Easy and long runs use this pace. Enter minutes and seconds, like 7:25, and choose per mile or per
                kilometer. Quality workouts stay on your 800.
              </p>
              {phrase ? <p className="rio-easy-now">{savedPaceLine(phrase)}</p> : null}
            </section>
            {paceError ? <p className="rio-error">{paceError}</p> : null}
            <form className="rio-easy-form" onSubmit={savePace} noValidate>
              <label htmlFor="profile-easy-pace">
                Easy pace
                <input
                  id="profile-easy-pace"
                  value={pace}
                  placeholder="7:25"
                  onChange={(event) => setPace(event.target.value)}
                />
              </label>
              <p className="rio-easy-hint">Minutes and seconds, like 7:25.</p>
              <fieldset>
                <legend>Unit</legend>
                <label>
                  <input type="radio" name="profile-easy-unit" checked={unit === "mi"} onChange={() => setUnit("mi")} />{" "}
                  per mile
                </label>
                <label>
                  <input type="radio" name="profile-easy-unit" checked={unit === "km"} onChange={() => setUnit("km")} />{" "}
                  per kilometer
                </label>
              </fieldset>
              <button className="rio-primary" type="submit" disabled={paceBusy}>
                Save easy pace
              </button>
            </form>
            {profile?.ready ? (
              <>
                <p className="rio-profile-lead">
                  Four values from Start. Current 800, the start date, and the goal date stay with the season. Goal
                  800m time is the one you can change.
                </p>
                <section className="rio-soft-card rio-profile-group">
                  <p className="rio-mark-label">Starting point</p>
                  <p className="rio-soft-help">Your current 800, and the day this season began.</p>
                  <FieldList fields={starting} dateFormat={dateFormat} />
                </section>
                <section className="rio-soft-card rio-profile-race">
                  <p className="rio-mark-label">The race</p>
                  <p className="rio-soft-help">
                    The day you are training toward, and the 800 time you want that day. The date stays with the
                    season.
                  </p>
                  <FieldList fields={goalDate} dateFormat={dateFormat} />
                  <form className="rio-profile-edit" onSubmit={saveGoal} noValidate>
                    <label htmlFor="profile-goal">
                      Goal 800m time
                      <input
                        id="profile-goal"
                        type="text"
                        value={goal}
                        placeholder="1:55.0"
                        onChange={(event) => setGoal(event.target.value)}
                      />
                    </label>
                    <p className="rio-profile-hint">Minutes, seconds, and tenths, like 1:55.0.</p>
                    <button className="rio-primary" type="submit" disabled={goalBusy}>
                      Save
                    </button>
                    <p className="rio-settings-note">
                      Saving keeps this time on your account. It does not rebuild the season.
                    </p>
                  </form>
                  {goalError ? <p className="rio-error">{goalError}</p> : null}
                  {profile.goal_override ? <p className="rio-settings-note">Saved for this account.</p> : null}
                </section>
              </>
            ) : null}
            {!failed && profile && !profile.ready ? (
              <>
                <p className="rio-empty">Generate a season on Start.</p>
                <p className="rio-season-prompt">
                  <Link href="/start">Generate season plan</Link>
                </p>
              </>
            ) : null}
          </>
        ) : null}
        <Footer />
      </main>
    </div>
  );
}

function FieldList({
  fields,
  dateFormat,
}: {
  fields: { label: string; value: string }[];
  dateFormat: string;
}) {
  return (
    <div className="rio-fields">
      {fields.map((field) => (
        <div className="rio-field" key={field.label}>
          <div className="rio-k">{field.label}</div>
          <div className="rio-v">{shownField(field.label, field.value, dateFormat)}</div>
        </div>
      ))}
    </div>
  );
}
