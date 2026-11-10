import type { CurrentSeason } from "./types";

/** Home when the goal date is today or later in the Settings time zone. */
export function landingPath(season: CurrentSeason | null): "/home" | "/start" {
  const goal = season?.inputs?.goal_date;
  const today = season?.today;
  if (!goal || !today) return "/start";
  return goal >= today ? "/home" : "/start";
}
