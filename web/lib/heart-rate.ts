/** Karvonen zones. The same percents and rounding as engines/heart_rate.py. */

export const METHOD_SENTENCE = "Zones use the Karvonen (heart rate reserve) method.";

export const SAFETY_NOTE =
  "This is not medical advice. Stop and seek help if your heart rate stays unusually high or you feel unwell.";

export const RESTING_ERROR = "Enter a resting heart rate between 30 and 100.";
export const MAX_ERROR = "Enter a max heart rate between 140 and 230.";
export const ORDER_ERROR = "Max heart rate has to be above resting heart rate.";
export const BOUND_ERROR = "Enter a heart rate between 30 and 230.";
export const ORDER_BOUND_ERROR = "Zone boundaries have to stay in order.";

const SPECS = [
  { zone: 1, key: "recovery", name: "Recovery", low: 50, high: 60 },
  { zone: 2, key: "easy", name: "Easy / long", low: 60, high: 70 },
  { zone: 3, key: "tempo", name: "Tempo", low: 70, high: 80 },
  { zone: 4, key: "threshold", name: "Threshold", low: 80, high: 90 },
  { zone: 5, key: "vo2", name: "VO2max / race", low: 90, high: 100 },
] as const;

export type ZoneDraft = {
  zone: number;
  key: string;
  name: string;
  lowPercent: number;
  highPercent: number;
  lowBpm: number;
  highBpm: number;
};

/** A later phase can estimate max heart rate from age. This phase does not. */
export function maxHrFromAge(age: number): null {
  if (!Number.isFinite(age)) return null;
  return null;
}

/** One decimal, or null when the text is not a real number. */
export function parseAnchor(value: string): number | null {
  const text = value.trim();
  if (!/^\d+(\.\d)?$/.test(text)) return null;
  const number = Number(text);
  if (!Number.isFinite(number)) return null;
  return Math.round(number * 10) / 10;
}

export function anchorError(resting: number | null, max: number | null): string {
  if (resting == null || resting < 30 || resting > 100) return RESTING_ERROR;
  if (max == null || max < 140 || max > 230) return MAX_ERROR;
  if (max <= resting) return ORDER_ERROR;
  return "";
}

/** Beats at this percent of heart-rate reserve, rounded half up. */
export function karvonenBpm(resting: number, max: number, percent: number): number {
  const rest = Math.round(resting * 10);
  const top = Math.round(max * 10);
  const rawTenths = rest + ((top - rest) * percent) / 100;
  return Math.round(rawTenths / 10);
}

export function karvonenZones(resting: number, max: number): ZoneDraft[] {
  return SPECS.map((spec) => ({
    zone: spec.zone,
    key: spec.key,
    name: spec.name,
    lowPercent: spec.low,
    highPercent: spec.high,
    lowBpm: karvonenBpm(resting, max, spec.low),
    highBpm: karvonenBpm(resting, max, spec.high),
  }));
}

export function zonesMatch(left: ZoneDraft[], right: ZoneDraft[]): boolean {
  return (
    left.length === right.length &&
    left.every((zone, index) => zone.lowBpm === right[index]?.lowBpm && zone.highBpm === right[index]?.highBpm)
  );
}

/** Move one edge and the shared edge of the neighboring zone. */
export function moveEdge(zones: ZoneDraft[], index: number, edge: "low" | "high", bpm: number): ZoneDraft[] {
  const next = zones.map((zone) => ({ ...zone }));
  const zone = next[index];
  if (!zone) return next;
  if (edge === "low") {
    zone.lowBpm = bpm;
    if (index > 0) next[index - 1].highBpm = bpm;
  } else {
    zone.highBpm = bpm;
    if (index < next.length - 1) next[index + 1].lowBpm = bpm;
  }
  return next;
}

export function boundsError(zones: ZoneDraft[]): string {
  for (let index = 0; index < zones.length; index += 1) {
    const zone = zones[index];
    if (zone.lowBpm < 30 || zone.lowBpm > 230 || zone.highBpm < 30 || zone.highBpm > 230) return BOUND_ERROR;
    if (zone.lowBpm >= zone.highBpm) return ORDER_BOUND_ERROR;
    if (index > 0 && zones[index - 1].highBpm !== zone.lowBpm) return ORDER_BOUND_ERROR;
  }
  return "";
}

export function formatRange(low: number, high: number): string {
  return `${low}\u2013${high}`;
}
