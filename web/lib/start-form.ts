export type SeasonInputs = {
  current_time: string;
  start_date: string;
  goal_time: string;
  goal_date: string;
};

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

function parts(iso: string): { year: number; month: number; day: number } | null {
  const match = ISO.exec(iso);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12 || day < 1) return null;
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  if (day > last) return null;
  return { year, month, day };
}

function isoFrom(year: number, month: number, day: number): string {
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const kept = Math.min(day, last);
  const monthText = String(month).padStart(2, "0");
  const dayText = String(kept).padStart(2, "0");
  return `${year}-${monthText}-${dayText}`;
}

/** Calendar months after an ISO day. A shorter month keeps its last day. */
export function monthsLater(iso: string, months: number): string {
  const found = parts(iso);
  if (!found || !Number.isInteger(months) || months < 0) {
    throw new Error("today is not a calendar date");
  }
  const index = found.month - 1 + months;
  const year = found.year + Math.floor(index / 12);
  const month = (index % 12) + 1;
  return isoFrom(year, month, found.day);
}

/** Sunday stays Sunday. Any other day moves forward to Sunday. */
export function startOn(iso: string, behavior: unknown): string {
  const found = parts(iso);
  if (!found) throw new Error("today is not a calendar date");
  if (behavior !== "sunday") return iso;
  const weekday = new Date(Date.UTC(found.year, found.month - 1, found.day)).getUTCDay();
  const shift = (7 - weekday) % 7;
  const moved = new Date(Date.UTC(found.year, found.month - 1, found.day + shift));
  return isoFrom(moved.getUTCFullYear(), moved.getUTCMonth() + 1, moved.getUTCDate());
}

/** Blank times, today (or the next Sunday), and five calendar months after today. */
export function startFormDefaults(today: string, behavior: unknown): {
  currentTime: string;
  startDate: string;
  goalTime: string;
  goalDate: string;
} {
  const found = parts(today);
  if (!found) throw new Error("today is not a calendar date");
  return {
    currentTime: "",
    startDate: startOn(today, behavior),
    goalTime: "",
    goalDate: monthsLater(today, 5),
  };
}

export function linkFromParams(params: { get(name: string): string | null }): SeasonInputs | null {
  const current_time = (params.get("current_time") || "").trim();
  const start_date = (params.get("start_date") || "").trim();
  const goal_time = (params.get("goal_time") || "").trim();
  const goal_date = (params.get("goal_date") || "").trim();
  const fields = [current_time, start_date, goal_time, goal_date];
  if (fields.some((field) => !field || field.length > 40)) return null;
  return { current_time, start_date, goal_time, goal_date };
}

export function sameSeason(
  saved: Partial<SeasonInputs> | null | undefined,
  link: SeasonInputs,
): boolean {
  if (!saved?.current_time || !saved.start_date || !saved.goal_time || !saved.goal_date) return false;
  return (
    saved.current_time === link.current_time &&
    saved.start_date === link.start_date &&
    saved.goal_time === link.goal_time &&
    saved.goal_date === link.goal_date
  );
}

export function planHasScore(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  if (Array.isArray(value)) return value.some(planHasScore);
  const record = value as Record<string, unknown>;
  if ("probability" in record || "readiness_score" in record) return true;
  return Object.values(record).some(planHasScore);
}

export function homeQuery(inputs: SeasonInputs, justGenerated: boolean): string {
  const params = new URLSearchParams({
    current_time: inputs.current_time,
    start_date: inputs.start_date,
    goal_time: inputs.goal_time,
    goal_date: inputs.goal_date,
  });
  if (justGenerated) params.set("just_generated", "true");
  return params.toString();
}
