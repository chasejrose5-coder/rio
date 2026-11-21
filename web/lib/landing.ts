import type { Athlete, CurrentSeason } from "./types";

export function needsEasyPace(athlete: Athlete | null): boolean {
  return !String(athlete?.prefs?.easy_pace || "").trim();
}

export type HeartGate = {
  no_monitor?: boolean;
  resting_hr?: number | null;
  max_hr?: number | null;
} | null;

/** True when this runner still needs the heart-rate step. A missing read does not block them. */
export function needsHeartRate(profile: HeartGate): boolean {
  if (!profile || profile.no_monitor) return false;
  return profile.resting_hr == null || profile.max_hr == null;
}

export function needsIntro(athlete: Athlete | null, season: CurrentSeason | null): boolean {
  if (athlete?.prefs?.intro_seen === true) return false;
  if (athlete?.prefs?.intro_seen === false) return true;
  return season == null;
}

/** The screen a signed-in runner should open, once the season read has finished. */
export function pathAfterSeason(athlete: Athlete, season: CurrentSeason | null): "/home" | "/start" | "/easy-pace" | "/intro" {
  if (needsEasyPace(athlete)) return "/easy-pace";
  if (needsIntro(athlete, season)) return "/intro";
  return landingPath(season);
}

export const HR_PROMPT_KEY = "rio_hr_prompt_dismissed";

/** Home shows the heart-rate card until this runner dismisses it or saves a reading. */
export function heartPromptOpen(profile: HeartGate, dismissed: boolean): boolean {
  if (dismissed) return false;
  return needsHeartRate(profile);
}

export const LANDING_KEY = "rio_landing";

/** Home when the goal date is today or later in the Settings time zone. */
export function landingPath(season: CurrentSeason | null): "/home" | "/start" {
  const goal = season?.inputs?.goal_date;
  const today = season?.today;
  if (!goal || !today) return "/start";
  return goal >= today ? "/home" : "/start";
}

export function rememberedLanding(): "/home" | "/start" | null {
  if (typeof window === "undefined") return null;
  const value = window.sessionStorage.getItem(LANDING_KEY);
  return value === "/home" || value === "/start" ? value : null;
}

export function rememberLanding(path: "/home" | "/start"): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(LANDING_KEY, path);
}

export function forgetLanding(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(LANDING_KEY);
}
