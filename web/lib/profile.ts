/** Profile display rules. The season stays the season. This file does not build one. */

const GOAL = /^(\d+):(\d{2})(\.\d+)?$/;
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;
const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const EASY = /^(\d{1,2}):([0-5]\d)$/;
const EASY_TRAIL = /^(\d{1,2}):([0-5]\d)\.0+$/;

export const GOAL_ERROR = "goal_time is not an 800 time";
export const PACE_ERROR = "Enter a pace like 7:25.";

export const MORE_LINKS = [
  { href: "/past-seasons", label: "Past seasons", blurb: "Seasons you have already saved." },
  { href: "/profile", label: "Profile", blurb: "Your current 800, goal, and dates." },
  { href: "/settings", label: "Settings", blurb: "Name, pace, and this account." },
  { href: "/about", label: "About", blurb: "Phases, the 10% rule, and what a mark changes." },
  { href: "/creators", label: "Creators", blurb: "Chase Rose, Founder." },
] as const;

/** An 800 time, or null. Blank and zero are not times. The text is kept as typed. */
export function cleanGoal(value: string): string | null {
  const text = value.trim();
  const match = GOAL.exec(text);
  if (!match) return null;
  let seconds = Number(match[1]) * 60 + Number(match[2]);
  if (match[3]) seconds += Number(match[3]);
  if (!(seconds > 0)) return null;
  return text;
}

/** 7:25, or null. Faster than 1:00 or slower than 30:00 is not stored. */
export function canonicalEasyPace(value: string): string | null {
  let text = value.trim();
  const trail = EASY_TRAIL.exec(text);
  if (trail) text = `${Number(trail[1])}:${trail[2]}`;
  const match = EASY.exec(text);
  if (!match) return null;
  const total = Number(match[1]) * 60 + Number(match[2]);
  if (total < 60 || total > 30 * 60) return null;
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function easyPacePhrase(pace: string, unit: string): string {
  const text = canonicalEasyPace(pace);
  if (!text) return "";
  return `${text} ${unit === "km" ? "per kilometer" : "per mile"}`;
}

export function savedPaceLine(phrase: string): string {
  const text = phrase.trim();
  if (!text) return "";
  return `Saved: ${text}. You can change it here.`;
}

/** ISO stays YYYY-MM-DD. Short is the same English day Plan uses, such as Mar 19, 2027. */
function profileDate(value: string, dateFormat: string): string {
  const text = value.trim();
  const match = ISO_DATE.exec(text);
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

/** A blank Start value is an em dash. Dates follow the saved format. */
export function shownField(label: string, value: string, dateFormat: string): string {
  const text = (value || "").trim();
  if (!text || text === "—") return "—";
  if (label === "Start date" || label === "Goal date") return profileDate(text, dateFormat);
  return text;
}
