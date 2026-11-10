import type { StoredSeason } from "./types";

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;
const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** ISO stays YYYY-MM-DD. Short is the same English day Plan uses, such as Oct 24, 2026. */
export function formatSeasonDate(value: string, dateFormat: string): string {
  const text = (value || "").trim();
  const match = ISO.exec(text);
  if (!match) return text || "—";
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) {
    return text || "—";
  }
  if (dateFormat === "short") return `${SHORT_MONTHS[month - 1]} ${day}, ${year}`;
  return text;
}

export type SeasonInputs = StoredSeason["inputs"];

/** Goal date of today is still current. A goal date before today is past. */
export function isPastSeason(goalDate: string, today: string): boolean {
  return Boolean(goalDate) && Boolean(today) && goalDate < today;
}

export function seasonKey(inputs: SeasonInputs): string {
  return [inputs.current_time, inputs.start_date, inputs.goal_time, inputs.goal_date].join("\n");
}

/** Every stored season, current ones included. Start date, then goal date, then goal time. */
export function seasonRows(past: StoredSeason[] | undefined, open: StoredSeason[] | undefined): StoredSeason[] {
  const seen = new Set<string>();
  const rows: StoredSeason[] = [];
  for (const row of [...(open || []), ...(past || [])]) {
    if (!row?.inputs) continue;
    const key = seasonKey(row.inputs);
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push(row);
  }
  rows.sort((left, right) => {
    const a = left.inputs;
    const b = right.inputs;
    return (
      a.start_date.localeCompare(b.start_date) ||
      a.goal_date.localeCompare(b.goal_date) ||
      a.goal_time.localeCompare(b.goal_time) ||
      a.current_time.localeCompare(b.current_time)
    );
  });
  return rows;
}

export function planQuery(inputs: SeasonInputs): string {
  const params = new URLSearchParams({
    current_time: inputs.current_time,
    start_date: inputs.start_date,
    goal_time: inputs.goal_time,
    goal_date: inputs.goal_date,
  });
  return `/plan?${params.toString()}`;
}

/** The three values a row shows, in the saved date format. */
export function rowValues(inputs: SeasonInputs, dateFormat: string): { start: string; goal: string; time: string } {
  return {
    start: formatSeasonDate(inputs.start_date, dateFormat),
    goal: formatSeasonDate(inputs.goal_date, dateFormat),
    time: inputs.goal_time,
  };
}

export function rowLabel(inputs: SeasonInputs, dateFormat: string): string {
  const shown = rowValues(inputs, dateFormat);
  return `${shown.start} ${shown.goal} ${shown.time}`;
}

export const UNREADABLE = "This account's seasons could not be read.";

export function unreadableMessage(message: string): string | null {
  if (message === UNREADABLE || message === "Accounts could not be read.") return UNREADABLE;
  return null;
}
