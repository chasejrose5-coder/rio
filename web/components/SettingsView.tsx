"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Expander } from "./Expander";
import { SecretField } from "./SecretField";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { StravaPanel } from "./StravaSettings";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  APP_VERSION,
  browserClearNote,
  downloadText,
  nameNote,
  normalizeName,
  seasonFile,
  TIME_ZONES,
  zoneOptions,
} from "@/lib/settings";
import type { Athlete } from "@/lib/types";

type Pace = "mi" | "km";
type StartOn = "today" | "sunday";
type Dates = "iso" | "short";

export function SettingsView() {
  return (
    <RequireUser>
      <SettingsBody />
    </RequireUser>
  );
}

function SettingsBody() {
  const router = useRouter();
  const params = useSearchParams();
  const flag = params.get("strava") || "";
  const { athlete, refresh, signOut } = useAuth();
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);
  const [seeded, setSeeded] = useState(false);
  const [problem, setProblem] = useState("");
  const [note, setNote] = useState("");
  const [name, setName] = useState("");
  const [preferred, setPreferred] = useState("");
  const [zone, setZone] = useState("UTC");
  const [pace, setPace] = useState<Pace>("mi");
  const [noWatch, setNoWatch] = useState(false);
  const [startOn, setStartOn] = useState<StartOn>("today");
  const [showIds, setShowIds] = useState(false);
  const [compact, setCompact] = useState(false);
  const [dates, setDates] = useState<Dates>("short");
  const [confirmAdapt, setConfirmAdapt] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [nextEmail, setNextEmail] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [clearMarksOk, setClearMarksOk] = useState(false);
  const [resetOk, setResetOk] = useState(false);
  const [deleteOk, setDeleteOk] = useState(false);
  const [deleteEmail, setDeleteEmail] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [clearOk, setClearOk] = useState(false);
  const [hasSeason, setHasSeason] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "settings";
    window.sessionStorage.setItem(key, "settings");
    if (first) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setArm(true);
    }
  }, []);

  useEffect(() => {
    if (!arm) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRise(true);
    const timer = window.setTimeout(() => setRise(false), 280);
    return () => window.clearTimeout(timer);
  }, [arm]);

  useEffect(() => {
    let live = true;
    api
      .currentSeason()
      .then((season) => {
        if (live) setHasSeason(season != null);
      })
      .catch((caught) => {
        if (!live) return;
        setHasSeason(false);
        setProblem(caught instanceof ApiError ? caught.message : "This account could not be opened.");
      });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (!athlete || seeded) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setName(athlete.display_name || "");
    setPreferred(String(athlete.prefs.preferred || ""));
    setZone(String(athlete.prefs.timezone || "UTC"));
    setPace(athlete.prefs.pace_units === "km" ? "km" : "mi");
    setNoWatch(athlete.prefs.no_watch === true);
    setStartOn(athlete.prefs.start_date === "sunday" ? "sunday" : "today");
    setShowIds(athlete.prefs.show_ids === true);
    setCompact(athlete.prefs.compact === true);
    setDates(athlete.prefs.date_format === "iso" ? "iso" : "short");
    setConfirmAdapt(athlete.prefs.confirm_adapt === true);
    setSeeded(true);
  }, [athlete, seeded]);

  useEffect(() => {
    if (!athlete || athlete.role === "admin" || athlete.prefs.show_ids !== true) return;
    let live = true;
    api
      .patchSettings({ show_ids: false })
      .then(() => {
        if (live) return refresh();
        return null;
      })
      .catch(() => {
        /* The toggle stays hidden. The next save can try again. */
      });
    return () => {
      live = false;
    };
  }, [athlete, refresh]);

  if (!athlete) return null;

  const user = athlete;
  const hosted = user.kind === "hosted";
  const admin = user.role === "admin";
  const zones = zoneOptions(zone);
  const clearNote = browserClearNote(athlete.kind);

  async function save(patch: Record<string, unknown>): Promise<Athlete | null> {
    setProblem("");
    try {
      const saved = await api.patchSettings(patch);
      await refresh();
      return saved;
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This account could not be saved.");
      return null;
    }
  }

  async function commitName() {
    const stored = athlete?.display_name || "";
    const cleaned = normalizeName(name);
    if (!cleaned) {
      if (name.trim() || stored) setProblem("Enter a name.");
      return;
    }
    setName(cleaned);
    if (cleaned === stored) return;
    const saved = await save({ display_name: cleaned });
    if (saved) setName(saved.display_name || cleaned);
  }

  async function commitPreferred() {
    const stored = String(athlete?.prefs.preferred || "");
    if (!preferred.trim()) {
      setPreferred("");
      if (!stored) return;
      const saved = await save({ preferred: "" });
      if (saved) setPreferred("");
      return;
    }
    const cleaned = normalizeName(preferred);
    if (!cleaned) {
      setProblem("That nickname will not work.");
      return;
    }
    setPreferred(cleaned);
    if (cleaned === stored) return;
    const saved = await save({ preferred: cleaned });
    if (saved) setPreferred(String(saved.prefs.preferred || ""));
  }

  async function commitZone(next: string) {
    const previous = zone;
    setZone(next);
    if (!(TIME_ZONES as readonly string[]).includes(next)) return;
    if (next === String(athlete?.prefs.timezone || "")) return;
    const saved = await save({ timezone: next });
    if (!saved) setZone(previous);
    else setZone(String(saved.prefs.timezone || next));
  }

  async function commitPace(next: Pace) {
    const previous = pace;
    setPace(next);
    const saved = await save({ pace_units: next });
    if (!saved) setPace(previous);
  }

  async function commitNoWatch(next: boolean) {
    setNoWatch(next);
    const saved = await save({ no_watch: next });
    if (!saved) setNoWatch(!next);
  }

  async function commitStart(next: StartOn) {
    const previous = startOn;
    setStartOn(next);
    const saved = await save({ start_date: next });
    if (!saved) setStartOn(previous);
  }

  async function commitIds(next: boolean) {
    setShowIds(next);
    const saved = await save({ show_ids: next });
    if (!saved) setShowIds(!next);
  }

  async function commitCompact(next: boolean) {
    setCompact(next);
    const saved = await save({ compact: next });
    if (!saved) setCompact(!next);
  }

  async function commitDates(next: Dates) {
    const previous = dates;
    setDates(next);
    const saved = await save({ date_format: next });
    if (!saved) setDates(previous);
  }

  async function commitConfirm(next: boolean) {
    setConfirmAdapt(next);
    const saved = await save({ confirm_adapt: next });
    if (!saved) setConfirmAdapt(!next);
  }

  async function showIntro() {
    setProblem("");
    setNote("");
    try {
      await api.patchSettings({ intro_seen: false });
      await refresh();
      router.push("/intro");
    } catch (caught) {
      setProblem(
        caught instanceof ApiError ? caught.message : "The intro guide could not be saved. It will show again next time.",
      );
    }
  }

  async function changePassword(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setProblem("");
    setNote("");
    try {
      const saved = await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setNote(saved.message || "Password updated.");
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This session could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function changeEmail(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setProblem("");
    setNote("");
    try {
      const saved = await api.changeEmail(nextEmail, emailPassword);
      setNextEmail("");
      setEmailPassword("");
      setNote(saved.message || "Email updated.");
      await refresh();
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This account could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function exportSeason() {
    setProblem("");
    setNote("");
    if (hasSeason === false) {
      setProblem("Generate a season on Start.");
      return;
    }
    try {
      const season = await api.currentSeason();
      if (!season) {
        setHasSeason(false);
        setProblem("Generate a season on Start.");
        return;
      }
      downloadText("rio-season.json", seasonFile(season));
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This account could not be opened.");
    }
  }

  async function clearMarks() {
    setNote("");
    if (!clearMarksOk) {
      setProblem("Confirm to clear marks and actuals.");
      return;
    }
    if (hasSeason === false) {
      setProblem("Generate a season on Start.");
      return;
    }
    setBusy(true);
    setProblem("");
    try {
      const season = await api.currentSeason();
      if (!season) {
        setHasSeason(false);
        setProblem("Generate a season on Start.");
        return;
      }
      await api.clearMarks();
      setNote("Marks and actuals are cleared.");
      setClearMarksOk(false);
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This account could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function resetPlan() {
    setNote("");
    if (!resetOk) {
      setProblem("Confirm to reset the plan.");
      return;
    }
    setBusy(true);
    setProblem("");
    try {
      await api.resetPlan();
      router.push("/start");
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This account could not be saved.");
      setBusy(false);
    }
  }

  async function deleteAccount() {
    setNote("");
    if (!deleteOk) {
      setProblem("Confirm to delete this account.");
      return;
    }
    if (!hosted) {
      const typed = deleteEmail.trim().toLowerCase();
      if (typed !== user.email.trim().toLowerCase()) {
        setProblem("Confirm with your email to delete this account.");
        return;
      }
    }
    setBusy(true);
    setProblem("");
    try {
      await api.deleteAccount(
        hosted ? { confirm: true } : { confirm: true, email: deleteEmail.trim(), password: deletePassword },
      );
      await signOut();
      router.replace("/sign-in");
    } catch (caught) {
      setProblem(caught instanceof ApiError ? caught.message : "This account could not be saved.");
      setBusy(false);
    }
  }

  async function clearBrowser() {
    setNote("");
    if (!clearOk) {
      setProblem("Confirm to clear local data.");
      return;
    }
    setBusy(true);
    try {
      window.localStorage.clear();
      window.sessionStorage.clear();
    } catch {
      /* A blocked store still signs this browser out. */
    }
    await signOut();
    router.replace("/");
  }

  return (
    <div className={compact ? "page-settings is-compact" : "page-settings"}>
      <Nav active="More" />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>Settings</h1>
        </header>
        {problem ? <p className="rio-error">{problem}</p> : null}
        {note ? <p className="rio-settings-note rio-settings-flash">{note}</p> : null}

        <Expander title="Profile" defaultOpen>
          <p className="rio-mark-label">Profile</p>
          <label className="rio-stack" htmlFor="settings-name">
            Name
            <input
              id="settings-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              onBlur={() => void commitName()}
            />
          </label>
          <p className="rio-settings-note">{nameNote(user.kind)}</p>
          <label className="rio-stack" htmlFor="settings-preferred">
            Preferred name / nickname
            <input
              id="settings-preferred"
              value={preferred}
              onChange={(event) => setPreferred(event.target.value)}
              onBlur={() => void commitPreferred()}
            />
          </label>
          <label className="rio-stack" htmlFor="settings-email">
            Email
            <input id="settings-email" value={user.email} disabled />
          </label>
          <label className="rio-stack" htmlFor="settings-timezone">
            Time zone
            <select id="settings-timezone" value={zones.includes(zone) ? zone : zones[0]} onChange={(event) => void commitZone(event.target.value)}>
              {zones.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <form onSubmit={changePassword} noValidate>
            <label className="rio-stack" htmlFor="settings-current-password">
              Current password
              <SecretField
                id="settings-current-password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={setCurrentPassword}
              />
            </label>
            <label className="rio-stack" htmlFor="settings-new-password">
              New password
              <SecretField
                id="settings-new-password"
                autoComplete="new-password"
                value={newPassword}
                onChange={setNewPassword}
              />
            </label>
            <button className="rio-primary" type="submit" disabled={busy}>
              Change password
            </button>
          </form>
        </Expander>

        <Expander title="Logging" defaultOpen>
          <p className="rio-mark-label">Logging</p>
          <label className="rio-toggle">
            <input type="checkbox" checked={noWatch} onChange={(event) => void commitNoWatch(event.target.checked)} />
            {"I don't use a watch"}
          </label>
          <p className="rio-settings-note">Complete workouts with Done instead of entering splits.</p>
        </Expander>

        <Expander title="Preferences">
          <p className="rio-mark-label">Preferences</p>
          <fieldset className="rio-choice-set">
            <legend>Pace units</legend>
            <div className="rio-choice">
              <label>
                <input type="radio" name="settings-pace" checked={pace === "mi"} onChange={() => void commitPace("mi")} /> per mile
              </label>
              <label>
                <input type="radio" name="settings-pace" checked={pace === "km"} onChange={() => void commitPace("km")} /> per km
              </label>
            </div>
          </fieldset>
          <p className="rio-settings-note">Distances and paces on Activity, Home, and Plan use this. Reps stay in meters.</p>
          <button type="button" className="rio-settings-button" onClick={() => void showIntro()}>
            Show intro guide
          </button>
          <div hidden>
            <span>Metric</span>
            <span>Imperial</span>
            <span>Dark</span>
            <span>Notifications</span>
            <span>Workout reminders</span>
            <span>Weekly recap</span>
            <span>Placeholder. Nothing is sent.</span>
          </div>
          <fieldset className="rio-choice-set">
            <legend>Default start date</legend>
            <div className="rio-choice">
              <label>
                <input type="radio" name="settings-start" checked={startOn === "today"} onChange={() => void commitStart("today")} /> Today
              </label>
              <label>
                <input type="radio" name="settings-start" checked={startOn === "sunday"} onChange={() => void commitStart("sunday")} /> Next Sunday
              </label>
            </div>
          </fieldset>
          <p className="rio-settings-note">Next Sunday starts the training week.</p>
          {admin ? (
            <label className="rio-toggle">
              <input type="checkbox" checked={showIds} onChange={(event) => void commitIds(event.target.checked)} />
              Show template ids
            </label>
          ) : null}
          <label className="rio-toggle">
            <input type="checkbox" checked={compact} onChange={(event) => void commitCompact(event.target.checked)} />
            Compact mode
          </label>
          <fieldset className="rio-choice-set">
            <legend>Date format</legend>
            <div className="rio-choice">
              <label>
                <input type="radio" name="settings-dates" checked={dates === "iso"} onChange={() => void commitDates("iso")} /> ISO
              </label>
              <label>
                <input type="radio" name="settings-dates" checked={dates === "short"} onChange={() => void commitDates("short")} /> Short
              </label>
            </div>
          </fieldset>
          <label className="rio-toggle">
            <input type="checkbox" checked={confirmAdapt} onChange={(event) => void commitConfirm(event.target.checked)} />
            Ask me before a timed run changes later weeks
          </label>
        </Expander>

        <Expander title="Data">
          <p className="rio-mark-label">Data</p>
          {hasSeason ? (
            <button type="button" className="rio-settings-button" onClick={() => void exportSeason()}>
              Export season as JSON
            </button>
          ) : hasSeason === false ? (
            <p className="rio-settings-note">Generate a season on Start.</p>
          ) : (
            <p className="rio-wait">Loading</p>
          )}
        </Expander>

        <Expander title="Account">
          <p className="rio-mark-label">Account</p>
          <form onSubmit={changeEmail} noValidate>
            <label className="rio-stack" htmlFor="settings-new-email">
              New email
              <input
                id="settings-new-email"
                type="email"
                autoComplete="email"
                value={nextEmail}
                onChange={(event) => setNextEmail(event.target.value)}
              />
            </label>
            <label className="rio-stack" htmlFor="settings-email-password">
              Password
              <SecretField
                id="settings-email-password"
                autoComplete="current-password"
                value={emailPassword}
                onChange={setEmailPassword}
              />
            </label>
            <button className="rio-primary" type="submit" disabled={busy}>
              Change email
            </button>
          </form>
        </Expander>

        <Expander title="Privacy">
          <p className="rio-mark-label">Privacy</p>
          <p className="rio-settings-note">{clearNote}</p>
        </Expander>

        <Expander title="About">
          <p className="rio-mark-label">About</p>
          <p className="rio-settings-note">RIO {APP_VERSION}</p>
        </Expander>

        <Expander title="Strava" {...(flag ? { open: true } : {})}>
          <StravaPanel flag={flag} />
        </Expander>

        <p className="rio-danger-kicker">Danger zone</p>
        <p className="rio-settings-note">
          Reset the plan, delete this account, or clear this browser. These sit apart from the settings above.
        </p>
        <Expander title="Danger zone" className="rio-expander-danger">
          <p className="rio-mark-label">Data</p>
          <label className="rio-check">
            <input type="checkbox" checked={clearMarksOk} onChange={(event) => setClearMarksOk(event.target.checked)} />
            Confirm clear
          </label>
          <button type="button" className="rio-danger-button" disabled={busy} onClick={() => void clearMarks()}>
            Clear all marks / actuals
          </button>
          <label className="rio-check">
            <input type="checkbox" checked={resetOk} onChange={(event) => setResetOk(event.target.checked)} />
            Confirm reset
          </label>
          <button type="button" className="rio-danger-button" disabled={busy} onClick={() => void resetPlan()}>
            Reset plan
          </button>
          <p className="rio-settings-note">Reset removes stored seasons. The account stays.</p>
          <p className="rio-mark-label">Account</p>
          <p className="rio-settings-kept" aria-hidden="true">
            Delete account
          </p>
          {hosted ? null : (
            <>
              <label className="rio-stack" htmlFor="settings-delete-email">
                Type your email to confirm
                <input
                  id="settings-delete-email"
                  value={deleteEmail}
                  onChange={(event) => setDeleteEmail(event.target.value)}
                />
              </label>
              <label className="rio-stack" htmlFor="settings-delete-password">
                Password
                <SecretField
                  id="settings-delete-password"
                  autoComplete="current-password"
                  value={deletePassword}
                  onChange={setDeletePassword}
                />
              </label>
            </>
          )}
          <label className="rio-check">
            <input type="checkbox" checked={deleteOk} onChange={(event) => setDeleteOk(event.target.checked)} />
            I understand this permanently deletes my season and runs
          </label>
          <button type="button" className="rio-danger-button" disabled={busy} onClick={() => void deleteAccount()}>
            Delete my account
          </button>
          <p className="rio-mark-label">Privacy</p>
          <label className="rio-check">
            <input type="checkbox" checked={clearOk} onChange={(event) => setClearOk(event.target.checked)} />
            Clear data stored in this browser
          </label>
          <button type="button" className="rio-danger-button" disabled={busy} onClick={() => void clearBrowser()}>
            Clear local data
          </button>
          <p className="rio-settings-note">{clearNote}</p>
        </Expander>
        <Footer />
      </main>
    </div>
  );
}
