import type { CurrentSeason } from "./types";

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
