"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Footer } from "./Footer";
import { PageMeaning } from "./PageMeaning";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api, rememberRead } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { destinationAfterSignIn } from "@/lib/enter";
import {
  METHOD_SENTENCE,
  SAFETY_NOTE,
  anchorError,
  boundsError,
  formatRange,
  karvonenZones,
  moveEdge,
  parseAnchor,
  zonesMatch,
  type ZoneDraft,
} from "@/lib/heart-rate";
import { markHeartRateSaved, needsHeartRate } from "@/lib/landing";
import { PACE_ERROR, canonicalEasyPace } from "@/lib/profile";
import type { HeartRateProfile } from "@/lib/types";
import { ErrorText, LoadError } from "./ErrorText";

type Mode = "onboarding" | "settings";

function movingToReset(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.dataset.resetZones === "true";
}

function draftFrom(profile: HeartRateProfile): ZoneDraft[] | null {
  if (profile.resting_hr == null || profile.max_hr == null) return null;
  if (profile.custom && profile.zones.length === 5) {
    return profile.zones.map((zone) => ({
      zone: zone.zone,
      key: zone.key,
      name: zone.name,
      lowPercent: zone.low_percent,
      highPercent: zone.high_percent,
      lowBpm: zone.low_bpm,
      highBpm: zone.high_bpm,
    }));
  }
  return karvonenZones(profile.resting_hr, profile.max_hr);
}

function anchorText(saved: number | null, prefill: number | null): string {
  if (saved != null) return String(saved);
  if (prefill != null) return String(prefill);
  return "";
}

export function HeartRateForm({ profile, mode }: { profile: HeartRateProfile; mode: Mode }) {
  const router = useRouter();
  const { athlete, refresh } = useAuth();
  const [resting, setResting] = useState(anchorText(profile.resting_hr, profile.strava_prefill.resting_hr));
  const [max, setMax] = useState(anchorText(profile.max_hr, profile.strava_prefill.max_hr));
  const [noMonitor, setNoMonitor] = useState(profile.no_monitor);
  const [zones, setZones] = useState<ZoneDraft[] | null>(draftFrom(profile));
  const [custom, setCustom] = useState(profile.custom);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pace, setPace] = useState(String(athlete?.prefs.easy_pace || ""));
  const [unit, setUnit] = useState<"mi" | "km">(athlete?.prefs.easy_pace_unit === "km" ? "km" : "mi");
  const [paceError, setPaceError] = useState("");
  const savedAnchors = useRef({ resting: profile.resting_hr, max: profile.max_hr });
  const saveGeneration = useRef(0);
  const prefilled =
    profile.resting_hr == null &&
    profile.max_hr == null &&
    (profile.strava_prefill.resting_hr != null || profile.strava_prefill.max_hr != null);

  function showAnchors(nextResting: string, nextMax: string) {
    setResting(nextResting);
    setMax(nextMax);
    const problem = anchorError(parseAnchor(nextResting), parseAnchor(nextMax));
    if (problem) {
      setZones(null);
      setCustom(false);
      return;
    }
    setZones(karvonenZones(parseAnchor(nextResting) as number, parseAnchor(nextMax) as number));
    setCustom(false);
    setError("");
  }

  async function save(patch: Record<string, unknown>): Promise<HeartRateProfile | null> {
    const generation = saveGeneration.current + 1;
    saveGeneration.current = generation;
    setBusy(true);
    setError("");
    try {
      const saved = await api.saveHeartRate(patch);
      if (generation !== saveGeneration.current) return saved;
      setNoMonitor(saved.no_monitor);
      if (saved.resting_hr != null) setResting(String(saved.resting_hr));
      if (saved.max_hr != null) setMax(String(saved.max_hr));
      setZones(draftFrom(saved));
      setCustom(saved.custom);
      savedAnchors.current = { resting: saved.resting_hr, max: saved.max_hr };
      rememberRead("/heart-rate", saved);
      markHeartRateSaved(saved);
      return saved;
    } catch (caught) {
      if (generation === saveGeneration.current) {
        setError(caught instanceof ApiError ? caught.message : "Heart rate could not be saved.");
      }
      return null;
    } finally {
      if (generation === saveGeneration.current) setBusy(false);
    }
  }

  async function commitAnchors() {
    if (mode !== "settings" || noMonitor) return;
    const low = parseAnchor(resting);
    const high = parseAnchor(max);
    const problem = anchorError(low, high);
    if (problem) {
      setError(problem);
      return;
    }
    if (low === savedAnchors.current.resting && high === savedAnchors.current.max) return;
    await save({ resting_hr: low, max_hr: high, no_monitor: false });
  }

  async function commitBounds() {
    if (mode !== "settings" || !zones || noMonitor) return;
    const problem = boundsError(zones);
    if (problem) {
      setError(problem);
      return;
    }
    const low = parseAnchor(resting);
    const high = parseAnchor(max);
    const anchors = anchorError(low, high);
    if (anchors) {
      setError(anchors);
      return;
    }
    const defaults = karvonenZones(low as number, high as number);
    if (zonesMatch(zones, defaults)) {
      await save({ resting_hr: low, max_hr: high, no_monitor: false, reset: true });
      return;
    }
    await save({
      resting_hr: low,
      max_hr: high,
      no_monitor: false,
      zones: zones.map((zone) => ({ zone: zone.zone, low_bpm: zone.lowBpm, high_bpm: zone.highBpm })),
    });
  }

  async function onToggle(next: boolean) {
    setNoMonitor(next);
    setError("");
    if (mode !== "settings") return;
    if (next) {
      const saved = await save({ no_monitor: true });
      if (!saved) setNoMonitor(false);
      return;
    }
    if (profile.resting_hr != null && profile.max_hr != null) {
      const saved = await save({ no_monitor: false });
      if (!saved) setNoMonitor(true);
    }
  }

  async function resetZones() {
    const low = parseAnchor(resting);
    const high = parseAnchor(max);
    const problem = anchorError(low, high);
    if (problem) {
      setError(problem);
      return;
    }
    const defaults = karvonenZones(low as number, high as number);
    setZones(defaults);
    setCustom(false);
    setError("");
    if (mode === "settings") {
      await save({ resting_hr: low, max_hr: high, no_monitor: false, reset: true });
    }
  }

  async function finish(event: React.FormEvent) {
    event.preventDefault();
    if (mode !== "onboarding") return;
    if (noMonitor) {
      const saved = await save({ no_monitor: true });
      if (!saved) return;
    } else {
      const low = parseAnchor(resting);
      const high = parseAnchor(max);
      const problem = anchorError(low, high);
      if (problem) {
        setError(problem);
        return;
      }
      const saved = await save({ resting_hr: low, max_hr: high, no_monitor: false });
      if (!saved) return;
    }
    if (!athlete) return;
    await refresh();
    router.replace(await destinationAfterSignIn(athlete));
  }

  async function savePace(event: React.FormEvent) {
    event.preventDefault();
    const cleaned = canonicalEasyPace(pace);
    if (!cleaned) {
      setPaceError(PACE_ERROR);
      return;
    }
    setBusy(true);
    setPaceError("");
    try {
      const saved = await api.patchSettings({ easy_pace: cleaned, easy_pace_unit: unit });
      setPace(String(saved.prefs.easy_pace || cleaned));
      setUnit(saved.prefs.easy_pace_unit === "km" ? "km" : "mi");
      await refresh();
    } catch (caught) {
      setPaceError(caught instanceof ApiError ? caught.message : "Easy pace could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  const formClass = mode === "onboarding" ? "rio-easy-form" : "rio-hr-settings";

  return (
    <div className="rio-hr">
      <form className={formClass} onSubmit={finish} noValidate>
        <label className="rio-toggle">
          <input
            id="no-hr-monitor"
            type="checkbox"
            checked={noMonitor}
            onChange={(event) => void onToggle(event.target.checked)}
          />
          I don&apos;t have a heart rate monitor
        </label>
        {noMonitor ? (
          <p className="rio-settings-note">Easy and long runs keep using your easy pace.</p>
        ) : (
          <>
            <p className="rio-hr-method">{METHOD_SENTENCE}</p>
            <label className="rio-stack" htmlFor="resting-hr">
              Resting heart rate
              <input
                id="resting-hr"
                inputMode="decimal"
                autoComplete="off"
                value={resting}
                onChange={(event) => showAnchors(event.target.value, max)}
                onBlur={() => void commitAnchors()}
              />
            </label>
            <p className="rio-easy-hint">Measured lying in bed when you wake up.</p>
            <label className="rio-stack" htmlFor="max-hr">
              Max heart rate
              <input
                id="max-hr"
                inputMode="decimal"
                autoComplete="off"
                value={max}
                onChange={(event) => showAnchors(resting, event.target.value)}
                onBlur={() => void commitAnchors()}
              />
            </label>
            <p className="rio-easy-hint">The highest heart rate you can reach in a hard effort.</p>
            {prefilled ? <p className="rio-settings-note">Filled from Strava. Check it before you save.</p> : null}
            {zones ? (
              <>
                <ul className="rio-zone-list" aria-label="Heart rate zones">
                  {zones.map((zone) => (
                    <li key={zone.zone}>
                      <div>
                        <p className="rio-zone-name">
                          Zone {zone.zone} · {zone.name}
                        </p>
                        <p className="rio-zone-meta">
                          {formatRange(zone.lowPercent, zone.highPercent)}% of heart-rate reserve
                        </p>
                      </div>
                      <p className="rio-zone-bpm">{formatRange(zone.lowBpm, zone.highBpm)} bpm</p>
                    </li>
                  ))}
                </ul>
                {custom ? <p className="rio-settings-note">These boundaries are your edit.</p> : null}
              </>
            ) : null}
            {mode === "settings" && zones ? (
              <details className="rio-zone-adjust">
                <summary>Adjust zone boundaries</summary>
                <div className="rio-zone-edit">
                  {zones.map((zone, index) => (
                    <fieldset key={zone.zone}>
                      <legend>Zone {zone.zone}</legend>
                      <label>
                        Low
                        <input
                          aria-label={`Zone ${zone.zone} low`}
                          inputMode="numeric"
                          value={zone.lowBpm}
                          onChange={(event) => {
                            if (event.target.value.trim() === "") return;
                            const bpm = Math.round(Number(event.target.value));
                            if (!Number.isFinite(bpm)) return;
                            setZones((current) => (current ? moveEdge(current, index, "low", bpm) : current));
                            setCustom(true);
                          }}
                          onBlur={(event) => {
                            if (movingToReset(event.relatedTarget)) return;
                            void commitBounds();
                          }}
                        />
                      </label>
                      <label>
                        High
                        <input
                          aria-label={`Zone ${zone.zone} high`}
                          inputMode="numeric"
                          value={zone.highBpm}
                          onChange={(event) => {
                            if (event.target.value.trim() === "") return;
                            const bpm = Math.round(Number(event.target.value));
                            if (!Number.isFinite(bpm)) return;
                            setZones((current) => (current ? moveEdge(current, index, "high", bpm) : current));
                            setCustom(true);
                          }}
                          onBlur={(event) => {
                            if (movingToReset(event.relatedTarget)) return;
                            void commitBounds();
                          }}
                        />
                      </label>
                    </fieldset>
                  ))}
                </div>
                <button className="rio-settings-button" type="button" data-reset-zones="true" onClick={() => void resetZones()}>
                  Reset to Karvonen defaults
                </button>
              </details>
            ) : null}
          </>
        )}
        <p className="rio-hr-safety">{SAFETY_NOTE}</p>
        {error ? <ErrorText>{error}</ErrorText> : null}
        {mode === "onboarding" ? (
          <button className="rio-primary" type="submit" disabled={busy}>
            {noMonitor ? "Continue" : "Save heart rate"}
          </button>
        ) : null}
      </form>
      {mode === "settings" && noMonitor ? (
        <form className="rio-easy-form" onSubmit={savePace} noValidate>
          <label htmlFor="settings-easy-pace">Easy pace</label>
          <input
            id="settings-easy-pace"
            placeholder="7:25"
            value={pace}
            onChange={(event) => setPace(event.target.value)}
          />
          <p className="rio-easy-hint">Minutes and seconds, like 7:25.</p>
          <fieldset>
            <legend>Unit</legend>
            <label>
              <input type="radio" name="settings-hr-unit" checked={unit === "mi"} onChange={() => setUnit("mi")} /> per mile
            </label>
            <label>
              <input type="radio" name="settings-hr-unit" checked={unit === "km"} onChange={() => setUnit("km")} /> per kilometer
            </label>
          </fieldset>
          {paceError ? <ErrorText>{paceError}</ErrorText> : null}
          <button className="rio-primary" type="submit" disabled={busy}>
            Save easy pace
          </button>
        </form>
      ) : null}
    </div>
  );
}

export function HeartRateSettings() {
  const [profile, setProfile] = useState<HeartRateProfile | null>(null);
  const [note, setNote] = useState("");

  useEffect(() => {
    let live = true;
    api
      .heartRate()
      .then((body) => {
        if (live) setProfile(body);
      })
      .catch(() => {
        if (live) setNote("Heart rate could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, []);

  return (
    <>
      <p className="rio-mark-label">Heart rate</p>
      {note ? <p className="rio-settings-note">{note}</p> : null}
      {!profile && !note ? <p className="rio-wait">Loading</p> : null}
      {profile ? <HeartRateForm profile={profile} mode="settings" /> : null}
    </>
  );
}

function HeartRateStepBody() {
  const router = useRouter();
  const { athlete } = useAuth();
  const [profile, setProfile] = useState<HeartRateProfile | null>(null);
  const [problem, setProblem] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    api
      .heartRate()
      .then((body) => {
        if (live) setProfile(body);
      })
      .catch((caught) => {
        if (!live) return;
        setProblem(caught instanceof ApiError ? caught.message : "Heart rate could not be loaded.");
      });
    return () => {
      live = false;
    };
  }, [attempt]);

  useEffect(() => {
    if (!profile || !athlete || needsHeartRate(profile)) return;
    let live = true;
    void destinationAfterSignIn(athlete).then((path) => {
      if (live) router.replace(path);
    });
    return () => {
      live = false;
    };
  }, [profile, athlete, router]);

  return (
    <div className="page-plain">
      <Nav />
      <main>
        <section className="rio-easy">
          <p className="rio-easy-kicker">Start here</p>
          <h1>Heart rate</h1>
          <p>
            Resting heart rate is measured lying in bed when you wake up. Max heart rate is the highest you can reach
            in a hard effort. Both are required.
          </p>
        </section>
        {problem ? <LoadError message={problem} onRetry={() => setAttempt((value) => value + 1)} /> : null}
        {!profile && !problem ? <p className="rio-wait">Loading</p> : null}
        {profile && needsHeartRate(profile) ? <HeartRateForm profile={profile} mode="onboarding" /> : null}
        <PageMeaning page="heart-rate" />
        <Footer />
      </main>
    </div>
  );
}

export function HeartRateStep() {
  return (
    <RequireUser>
      <HeartRateStepBody />
    </RequireUser>
  );
}
