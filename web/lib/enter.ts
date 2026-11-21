import { api, prefetchHome } from "./api";
import { needsEasyPace, pathAfterSeason, rememberLanding } from "./landing";
import type { Athlete } from "./types";

export const MARK_INTRO_KEY = "rio_mark_intro";

export type AppPath = "/home" | "/start" | "/easy-pace" | "/intro";

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

export function destinationAfterSignIn(athlete: Athlete): Promise<AppPath> {
  if (destinationInflight) return destinationInflight;
  destinationInflight = resolveDestination(athlete).finally(() => {
    destinationInflight = null;
  });
  return destinationInflight;
}

async function resolveDestination(athlete: Athlete): Promise<AppPath> {
  // Heart rate is a prompt on Home, not a gate. A missing reading does not
  // change where sign-in, Google, or the splash sends this runner.
  if (needsEasyPace(athlete)) return "/easy-pace";
  void prefetchHome().catch(() => undefined);
  const season = await api.currentSeason();
  const path = pathAfterSeason(athlete, season);
  if (path === "/easy-pace" || path === "/intro") return path;
  rememberLanding(path);
  if (season && athlete.prefs?.intro_seen !== true) {
    if (path === "/home") markIntroLater();
    else void api.patchSettings({ intro_seen: true }).catch(() => undefined);
  }
  return path;
}
