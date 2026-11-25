/** Usual long run, stored as meters. The season engine places the Saturday rung. */

export const SIX_MILES_M = 9656;
export const MILE_M = 1609;
export const LONG_MIN_M = 5000;
export const LONG_MAX_M = 20000;

export const USUAL_LONG_LABEL = "Usual long run";
export const USUAL_LONG_HELP =
  "About how far your normal long run is right now. At 6 miles (9.7 km) or more, Saturday starts a mile shorter, then builds 500 m a week up to 20 km. Under that, it starts at your usual. The long run stays between 5 and 20 km.";
export const USUAL_LONG_LOCKED =
  "This season keeps the long runs it started with. You can change your usual long run when you start your next season.";
export const USUAL_LONG_HIGH =
  "RIO's Saturday long runs go up to 20 km (12.4 mi), so your plan starts at 20 km.";

export type DistanceUnits = "miles" | "km";

export function distanceUnits(units: unknown): DistanceUnits {
  return units === "km" ? "km" : "miles";
}

export function usualLongError(units: DistanceUnits): string {
  return units === "km" ? "Enter a distance between 5 and 42 km." : "Enter a distance between 3.2 and 26 mi.";
}

export function usualLongPlaceholder(units: DistanceUnits): string {
  return units === "km" ? "13" : "8";
}

export function usualLongUnitLabel(units: DistanceUnits): string {
  return units === "km" ? "km" : "mi";
}

/** Blank is unset. A bad distance is an error string. Otherwise meters. */
export function parseUsualLong(text: string, units: DistanceUnits): number | { error: string } | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const message = usualLongError(units);
  if (!/^\d{1,2}(\.\d)?$/.test(trimmed)) return { error: message };
  const value = Number(trimmed);
  if (units === "km") {
    if (value < 5 || value > 42) return { error: message };
    return Math.round(value * 1000);
  }
  if (value < 3.2 || value > 26) return { error: message };
  return Math.round(value * 1609.344);
}

export function formatUsualLong(meters: number, units: DistanceUnits): string {
  if (!Number.isFinite(meters) || meters <= 0) return "";
  const value = units === "miles" ? meters / 1609.344 : meters / 1000;
  const shown = Math.round(value * 10) / 10;
  if (!Number.isFinite(shown) || shown <= 0) return "";
  return Number.isInteger(shown) ? String(shown) : shown.toFixed(1);
}

/** The week-1 rung. Same rule as engines.season.long_run_start_meters. */
export function longRunStartMeters(usual: number): number {
  const target = usual >= SIX_MILES_M ? usual - MILE_M : usual;
  const rung = Math.floor(target / 500) * 500;
  return Math.min(LONG_MAX_M, Math.max(LONG_MIN_M, rung));
}

export function usualLongNote(meters: number | null | undefined): string {
  if (meters == null || !Number.isFinite(meters) || meters <= 0) return "";
  const target = meters >= SIX_MILES_M ? meters - MILE_M : meters;
  const rung = Math.floor(target / 500) * 500;
  if (rung > LONG_MAX_M) return USUAL_LONG_HIGH;
  return "";
}
