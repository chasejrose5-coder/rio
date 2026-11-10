/** Display rules for Plan. The pace clock stays on GET /plan. This file does not invent a pace. */

export const PLAN_VIEWS = ["Calendar", "This week", "Full season"] as const;
export type PlanViewName = (typeof PLAN_VIEWS)[number];

export const MARKS = ["on_track", "not_hitting", "smashing"] as const;
export type MarkChoice = (typeof MARKS)[number];

const MARK_LABEL: Record<string, string> = {
  on_track: "On track",
  not_hitting: "Not hitting",
  smashing: "Smashing",
};

const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const STATUS_LABELS: [string, string][] = [
  ["harder_template", "Harder"],
  ["extra_easy_week", "Easy week"],
  ["extra_easy_day", "Easy"],
  ["ten_percent_hold", "Hold"],
  ["ten_percent_easier_template", "Easier"],
  ["weekly_aerobic_long_run", "Long"],
  ["moved_back_one_phase", "Moved back"],
  ["advanced_one_phase", "Advanced"],
  ["phase_8_freshness", "Fresh"],
  ["phase_8_no_hard_se_or_an", "Taper"],
  ["priority_speed_endurance", "Speed endurance"],
  ["priority_aerobic_power", "Aerobic power"],
  ["priority_anaerobic_capacity", "Anaerobic"],
  ["phase_primary", "Primary"],
  ["phase_secondary", "Secondary"],
  ["capacity_weight", "Weighted"],
];

const REASON_PLAIN: Record<string, string> = {
  phase_1: "Phase 1",
  phase_2: "Phase 2",
  phase_3: "Phase 3",
  phase_4: "Phase 4",
  phase_5: "Phase 5",
  phase_6: "Phase 6",
  phase_7: "Phase 7",
  phase_8: "Phase 8",
  phase_primary: "Primary work for this phase",
  phase_secondary: "Secondary work for this phase",
  weekly_aerobic_long_run: "The weekly long run",
  priority_speed_endurance: "Speed endurance is a priority",
  priority_aerobic_power: "Aerobic power is a priority",
  priority_anaerobic_capacity: "Anaerobic capacity is a priority",
  capacity_weight: "The higher capacity weight won",
  ten_percent_hold: "Held so the week does not rise more than 10%",
  ten_percent_easier_template: "An easier session, so the week stays within 10%",
  extra_easy_day: "An extra easy day",
  extra_easy_week: "An easy week",
  harder_template: "A harder session",
  moved_back_one_phase: "Moved back one phase",
  advanced_one_phase: "Advanced one phase",
  phase_8_freshness: "The taper stays fresh",
  phase_8_no_hard_se_or_an: "No hard speed endurance or anaerobic work",
};

const NEXT_WEEK: [string, string][] = [
  ["extra_easy_week", "Next week is an easy week."],
  ["harder_template", "Next week uses a harder session."],
  ["moved_back_one_phase", "Next week moves back one phase."],
  ["advanced_one_phase", "Next week advances one phase."],
];

const M_TO_MI = 1 / 1609.344;
const TIME = /^\d+:\d{2}(\.\d+)?$/;
const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

export type PlanSession = {
  date?: string;
  shown_date?: string;
  day_of_week?: string;
  week_number?: number;
  template_id?: string;
  label?: string;
  target?: string;
  reason_codes?: string[];
  prescription?: { line?: string; tolerance?: string; block?: string } | null;
};

export type ActualRow = {
  template_id?: string;
  completed?: boolean;
  missed?: boolean;
  numbers?: unknown[];
  slots?: unknown[];
  mark?: string;
};

export function isPlanView(value: string | null): value is PlanViewName {
  return value === "Calendar" || value === "This week" || value === "Full season";
}

export function lengthText(length: number): string {
  if (!Number.isInteger(length) || length <= 0) return "—";
  if (length === 1) return "1 week";
  return `${length} weeks`;
}

export function markLabel(mark: string | null | undefined): string {
  const text = (mark || "").trim();
  if (!text) return "—";
  return MARK_LABEL[text] || text.replaceAll("_", " ");
}

export function plainMarks(text: string): string {
  let shown = text;
  for (const [raw, label] of Object.entries(MARK_LABEL)) {
    shown = shown.replaceAll(raw, label);
  }
  return shown;
}

export function formatDate(value: string, dateFormat: string): string {
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

export function monthTitle(iso: string): string {
  const match = ISO.exec(iso) || /^(\d{4})-(\d{2})$/.exec(iso);
  if (!match) return iso;
  const month = Number(match[2]);
  if (month < 1 || month > 12) return iso;
  return `${MONTHS[month - 1]} ${match[1]}`;
}

export function monthKey(iso: string): string {
  return iso.slice(0, 7);
}

function parseUtc(iso: string): Date | null {
  const match = ISO.exec(iso);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
  return date;
}

function isoFrom(date: Date): string {
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${date.getUTCFullYear()}-${month}-${day}`;
}

export function addDays(iso: string, days: number): string {
  const date = parseUtc(iso);
  if (!date) return iso;
  date.setUTCDate(date.getUTCDate() + days);
  return isoFrom(date);
}

export function weekdayName(iso: string): string {
  const date = parseUtc(iso);
  if (!date) return "";
  return WEEKDAYS[date.getUTCDay()];
}

export function weekSunday(start: string, weekNumber: number): string {
  const date = parseUtc(start);
  if (!date) return start;
  const anchor = addDays(start, -date.getUTCDay());
  return addDays(anchor, (weekNumber - 1) * 7);
}

export function weekContaining(start: string, length: number, day: string): number {
  if (!Number.isInteger(length) || length <= 0) return 1;
  const sunday = weekSunday(start, 1);
  if (day < sunday) return 1;
  const startDate = parseUtc(sunday);
  const dayDate = parseUtc(day);
  if (!startDate || !dayDate) return 1;
  const number = Math.floor((dayDate.getTime() - startDate.getTime()) / 86400000 / 7) + 1;
  if (number > length) return length;
  return Math.max(1, number);
}

export function weekOption(start: string, weekNumber: number, dateFormat: string): string {
  const sunday = weekSunday(start, weekNumber);
  const saturday = addDays(sunday, 6);
  return `Week ${weekNumber} · ${formatDate(sunday, dateFormat)} — ${formatDate(saturday, dateFormat)}`;
}

export function weekSpan(start: string, weekNumber: number, phase: string, dateFormat: string): string {
  const sunday = weekSunday(start, weekNumber);
  const saturday = addDays(sunday, 6);
  const span = `${formatDate(sunday, dateFormat)} — ${formatDate(saturday, dateFormat)}`;
  if (!phase || phase === "—") return span;
  return `Phase ${phase} · ${span}`;
}

export function daysLabel(days: number | null | undefined): string {
  if (days == null) return "—";
  const noun = days === 1 ? "day" : "days";
  return `${days} ${noun} to goal`;
}

export function statusLabel(codes: string[] | undefined): string {
  const list = codes || [];
  const present = new Set(list.map(String));
  for (const [code, label] of STATUS_LABELS) {
    if (present.has(code)) return label;
  }
  for (const code of list) {
    const text = String(code);
    if (text.length === 7 && text.startsWith("phase_") && /\d/.test(text[6] || "")) continue;
    return text.replaceAll("_", " ");
  }
  return "";
}

export function plainReason(code: string): string {
  const text = code.trim();
  if (!text) return "";
  const known = REASON_PLAIN[text];
  if (known) return known;
  if (text.length === 7 && text.startsWith("phase_") && /\d/.test(text[6] || "")) return `Phase ${text[6]}`;
  return text.replaceAll("_", " ");
}

export function plainReasonLines(codes: string[] | undefined): string[] {
  const lines: string[] = [];
  for (const code of codes || []) {
    const words = plainReason(String(code));
    if (words) lines.push(words);
  }
  return lines;
}

function milesLabel(meters: number): string {
  const miles = meters * M_TO_MI;
  if (Math.abs(miles) >= 0.1) return `${miles.toFixed(1)} mi`;
  return `${miles.toFixed(2)} mi`;
}

/** Distance labels. Rep chunks are not rewritten here; Plan volume is a meter total. */
export function displayDistance(text: string, units: string): string {
  if (!text) return "";
  if (units === "miles") {
    const kilometers = text.replace(/(\d+(?:\.\d+)?)\s*km\b/gi, (_full, raw: string) => {
      const miles = Number(raw) * 0.621371;
      return `${miles.toFixed(1)} mi`;
    });
    return kilometers.replace(/(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*m\b/g, (_full, raw: string) => {
      return milesLabel(Number(String(raw).replace(/,/g, "")));
    });
  }
  return text.replace(/(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*m\b/g, (full, raw: string, offset: number, source: string) => {
    const meters = Number(String(raw).replace(/,/g, ""));
    if (!Number.isFinite(meters) || meters < 1000) return full;
    const prefix = source.slice(Math.max(0, offset - 4), offset);
    if (/(?:×|(?<![A-Za-z])x)\s*$/i.test(prefix)) return full;
    const km = meters / 1000;
    const shown = Number.isInteger(km) ? String(km) : km.toFixed(1);
    return `${shown} km`;
  });
}

export function volumeLabel(meters: number, volume: string, units: string): string {
  if (meters === 0) return "No runs logged";
  return displayDistance(volume || "—", units) || "—";
}

function weekRows<T extends { week_number?: number; date?: string }>(sessions: T[], week: number): T[] {
  if (!Number.isInteger(week)) return [];
  return sessions
    .filter((session) => session.week_number === week)
    .slice()
    .sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")));
}

function weekMark(marks: Record<string, string> | null | undefined, week: number): string | null {
  if (!marks || !Number.isInteger(week)) return null;
  const mark = marks[String(week)];
  if (mark === "on_track" || mark === "not_hitting" || mark === "smashing") return mark;
  return null;
}

function savedActual(session: { date?: string; template_id?: string }, actuals: Record<string, ActualRow>): ActualRow | null {
  const row = actuals[String(session.date || "")];
  if (!row || row.template_id !== session.template_id) return null;
  return row;
}

function isCompleted(row: ActualRow): boolean {
  if (row.missed === true && row.completed !== true) return false;
  if (row.completed === true) return true;
  if (Array.isArray(row.numbers) && row.numbers.some((item) => typeof item !== "boolean")) return true;
  return row.mark === "on_track" || row.mark === "not_hitting" || row.mark === "smashing";
}

function meterText(meters: number): string {
  if (!Number.isFinite(meters) || meters < 0) return "—";
  return `${Math.round(meters).toLocaleString("en-US")} m`;
}

function weekMeters(rows: { date?: string }[], distances: Record<string, number>): number {
  let total = 0;
  let any = false;
  for (const session of rows) {
    const day = session.date;
    if (!day || !(day in distances)) continue;
    const meters = distances[day];
    if (typeof meters !== "number" || !Number.isFinite(meters) || meters < 0) continue;
    total += meters;
    any = true;
  }
  if (!any) return 0;
  return Math.round(total);
}

export function recapView(input: {
  week: number;
  sessions: PlanSession[];
  actuals: Record<string, ActualRow>;
  marks: Record<string, string>;
  distances: Record<string, number>;
}): { completed: string; marks: string; volume: string; next: string } {
  const rows = weekRows(input.sessions, input.week);
  const previous = weekRows(input.sessions, input.week - 1);
  const following = weekRows(input.sessions, input.week + 1);
  const mark = weekMark(input.marks, input.week);
  const done = rows.filter((session) => {
    const saved = savedActual(session, input.actuals);
    return saved != null && isCompleted(saved);
  }).length;
  let completed = "—";
  if (done === 0 && mark) completed = "Marked";
  else if (rows.length) completed = `${done} of ${rows.length}`;

  const found: string[] = [];
  const seen: string[] = [];
  for (const session of rows) {
    const saved = savedActual(session, input.actuals);
    if (!saved) continue;
    const sessionMark = saved.mark;
    if (sessionMark !== "on_track" && sessionMark !== "not_hitting" && sessionMark !== "smashing") continue;
    if (!seen.includes(sessionMark)) seen.push(sessionMark);
    const day = (session.day_of_week || "").trim();
    found.push(day ? `${day} ${sessionMark}` : sessionMark);
  }
  if (mark && !seen.includes(mark)) found.push(mark);
  const marks = found.length ? plainMarks(found.join(" · ")) : "—";

  const current = meterText(weekMeters(rows, input.distances));
  const volume = previous.length ? `${current} · ${meterText(weekMeters(previous, input.distances))} the week before` : current;

  let next = "This is the last week.";
  if (following.length) {
    const codes: string[] = [];
    for (const session of following) {
      for (const code of session.reason_codes || []) {
        const text = String(code);
        if (!codes.includes(text)) codes.push(text);
      }
    }
    next = "Next week stays as written.";
    for (const [code, sentence] of NEXT_WEEK) {
      if (codes.includes(code)) {
        next = sentence;
        break;
      }
    }
  }
  return { completed, marks, volume, next };
}

export function distancesFromRows(rows: { date?: string; meters?: number | null }[]): Record<string, number> {
  const found: Record<string, number> = {};
  for (const row of rows) {
    if (!row.date || typeof row.meters !== "number" || !Number.isFinite(row.meters) || row.meters < 0) continue;
    found[row.date] = row.meters;
  }
  return found;
}

export function extrasBetween<T extends { date?: string; extra?: boolean }>(rows: T[], start: string, end: string): T[] {
  return rows.filter((row) => row.extra === true && typeof row.date === "string" && row.date >= start && row.date <= end);
}

/** A shared link that sequence() will not build. Blank when the URL is not that link. */
export function linkError(params: URLSearchParams): string {
  const current = params.get("current_time");
  const start = params.get("start_date");
  const goal = params.get("goal_time");
  const goalDate = params.get("goal_date");
  if (current == null && start == null && goal == null && goalDate == null) return "";
  if (!current || !start || !goal || !goalDate) return "";
  if (!TIME.test(current.trim())) return "current_time is not an 800 time";
  if (!TIME.test(goal.trim())) return "goal_time is not an 800 time";
  if (!ISO.test(start.trim())) return "start_date is not a calendar date";
  if (!ISO.test(goalDate.trim())) return "goal_date is not a calendar date";
  if (goalDate.trim() < start.trim()) return "goal_date is before start_date";
  return "";
}

export function paceStatusLine(status: string | undefined): string {
  const text = (status || "No runs yet").trim() || "No runs yet";
  return `Pace status ${text}.`;
}
