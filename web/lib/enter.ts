import { api, prefetchHome } from "./api";
import { needsEasyPace, needsHeartRate, pathAfterSeason, rememberLanding } from "./landing";
import type { Athlete, HeartRateProfile } from "./types";

export const MARK_INTRO_KEY = "rio_mark_intro";

export type AppPath = "/home" | "/start" | "/easy-pace" | "/intro" | "/heart-rate";

export function markIntroLater(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(MARK_INTRO_KEY, "1");
}

/** Home claims the flag once its prefetched payload is on screen. */
export function takeIntroMark(): boolean {
  if (typeof window === "undefined") return false;
  if (window.sessionStorage.getItem(MARK_INTRO_KEY) !== "1") return false;
  window.sessionStorage.removeItem(MARK_INTRO_KEY);
  return true;
}

/**
 * Where a signed-in runner goes, without a stop on `/`.
 * Home's GET is started here and reused by the Home screen.
 * The intro flag is saved after that read, so the write cannot drop it.
 */
let destinationInflight: Promise<AppPath> | null = null;

/** Start the reads sign-in needs so they overlap the session probe. */
export function warmDestinationReads(): void {
  void api.heartRate().catch(() => undefined);
  void api.currentSeason().catch(() => undefined);
}

export function destinationAfterSignIn(athlete: Athlete): Promise<AppPath> {
  if (destinationInflight) return destinationInflight;
  destinationInflight = resolveDestination(athlete).finally(() => {
    destinationInflight = null;
  });
  return destinationInflight;
}

async function readHeartRate(): Promise<HeartRateProfile | null> {
  try {
    return await api.heartRate();
  } catch {
    return null;
  }
}

async function resolveDestination(athlete: Athlete): Promise<AppPath> {
  const heartPromise = readHeartRate();
  const seasonPromise = needsEasyPace(athlete) ? null : api.currentSeason();
  const heart = await heartPromise;
  if (needsHeartRate(heart)) return "/heart-rate";
  if (needsEasyPace(athlete)) return "/easy-pace";
  void prefetchHome().catch(() => undefined);
  const season = await (seasonPromise ?? api.currentSeason());
  const path = pathAfterSeason(athlete, season);
  if (path === "/easy-pace" || path === "/intro") return path;
  rememberLanding(path);
  if (season && athlete.prefs?.intro_seen !== true) {
    if (path === "/home") markIntroLater();
    else void api.patchSettings({ intro_seen: true }).catch(() => undefined);
  }
  return path;
}
