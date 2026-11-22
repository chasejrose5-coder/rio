/** Session page copy and the result boxes. Pace stays on GET /sessions.

Easy-day warm-up matches engines/warmup.py. The same session always gets the same notes.
 */

export type SessionKind = "easy" | "long" | "race" | "quality" | "rest";

export type PrepBlock = {
  title: string;
  lines?: readonly string[];
  lead?: readonly string[];
  groups?: readonly (readonly string[])[];
};

const RACE_ID = "rr_800_r0_x1";

const COOLDOWN: PrepBlock = {
  title: "Cool-down",
  lead: ["1 easy lap, then seated stretches for the full lower body:"],
  groups: [
    [
      "Seated forward fold",
      "Seated figure-four each side",
      "Seated straddle",
      "Seated hip-flexor each side",
      "Seated calf stretch each side",
      "Seated hamstring each side",
      "Lying spinal twist each side",
    ],
  ],
};

const CORE: PrepBlock = {
  title: "Core",
  lead: ["3 rounds of:"],
  groups: [
    [
      "Plank",
      "Side plank each side",
      "Dead bug each side",
      "Bird-dog each side",
      "Glute bridge",
      "Bicycle crunch each side",
      "Reverse crunch",
      "Split-lunge jumps (low volume)",
    ],
  ],
};

const EASY_WARM: PrepBlock = {
  title: "Warm-up",
  lines: ["3–5 min easy jog"],
  lead: ["Then leg swings and a few light stretches:"],
  groups: [["Lateral leg swings", "Walking quad stretch", "Hamstring sweeps", "Easy calf stretch each side"]],
};

const FULL_WARM: PrepBlock = {
  title: "Warm-up",
  lead: ["Active drills (20–30 m each):", "Dynamic drills (20–30 m each):", "Then:"],
  groups: [
    [
      "Arm swings forward and reverse",
      "Walking quad stretch",
      "Hamstring sweeps",
      "Lateral leg swings",
      "Alternating knee drops",
      "Rocking adductor stretch",
    ],
    ["A-skips", "B-skips", "Knee buffs", "Straight-leg bounds", "Lateral skips"],
    ["4 × 100 m strides with walk-back"],
  ],
};

const PRE_WARM: PrepBlock = {
  title: "Pre-warm-up",
  lines: ["1 × 800 m easy"],
};

/** Full warm-up. Easy days use prepFor instead. */
export const PREP = [PRE_WARM, FULL_WARM, COOLDOWN, CORE] as const;

type KindSession = {
  template_id?: string;
  day_of_week?: string;
  reason_codes?: readonly string[];
} | null | undefined;

function longLadder(template: string): boolean {
  const match = /^aer_(\d+)_r0_x1$/.exec(template);
  if (!match) return false;
  const meters = Number(match[1]);
  return meters >= 9500 && meters <= 15000 && (meters - 9500) % 500 === 0;
}

/** Same rule as engines/bike.py day_kind. */
export function sessionKind(session: KindSession): SessionKind {
  if (!session) return "rest";
  const template = (session.template_id || "").trim();
  if (!template) return "rest";
  if (template === RACE_ID) return "race";
  const codes = session.reason_codes || [];
  const dow = (session.day_of_week || "").trim();
  const longCoded = codes.includes("weekly_aerobic_long_run") || longLadder(template);
  if (dow === "Saturday" && longCoded) return "long";
  if (template.startsWith("aer_") || codes.includes("extra_easy_day")) return "easy";
  return "quality";
}

/** Easy runs: a short jog, leg swings, and a few light stretches. No drills, no strides. */
export function prepFor(session: KindSession): PrepBlock[] {
  if (sessionKind(session) === "easy") return [EASY_WARM, COOLDOWN, CORE];
  return [PRE_WARM, FULL_WARM, COOLDOWN, CORE];
}

const OUTCOME: Record<string, string> = {
  not_hitting: "Behind",
  on_track: "On track",
  smashing: "Ahead",
};

export function sessionHref(next: string | null | undefined): string {
  if (typeof next === "string" && /^\d{4}-\d{2}-\d{2}$/.test(next)) return `/session?date=${next}`;
  return "/session";
}

/** The next planned day from a season payload, or the last day when the season is over. */
export function nextSessionDate(season: { today?: string; plan?: { sessions?: { date?: string }[] } } | null): string | null {
  const today = season?.today || "";
  const days = (season?.plan?.sessions || [])
    .map((row) => row.date || "")
    .filter((day) => /^\d{4}-\d{2}-\d{2}$/.test(day))
    .sort();
  if (!days.length) return null;
  return days.find((day) => !today || day >= today) || days[days.length - 1];
}

export function timeToken(value: string): string | null {
  const text = value.trim();
  if (!/^\d+(\.\d+)?$/.test(text)) return null;
  const number = Number(text);
  if (!Number.isFinite(number) || number <= 0) return null;
  const rounded = Math.round(number * 100) / 100;
  if (Number.isInteger(rounded)) return String(rounded);
  return String(rounded);
}

export function filledTimes(values: string[]): string {
  return values
    .map((value) => timeToken(value))
    .filter((item): item is string => item !== null)
    .join(", ");
}

/** A keystroke that is not part of a time is ignored. */
export function acceptTimeKey(current: string, next: string): string {
  if (next === "") return "";
  if (/^\d*\.?\d*$/.test(next)) return next;
  return current;
}

export function slotsFrom(values: string[]): (number | null)[] {
  return values.map((value) => {
    const token = timeToken(value);
    return token === null ? null : Number(token);
  });
}

export function fitSlots(times: (number | null)[] | undefined, count: number): string[] {
  const slots = Array.from({ length: count }, () => "");
  (times || []).slice(0, count).forEach((value, index) => {
    if (typeof value === "number" && Number.isFinite(value) && value > 0) slots[index] = String(value);
  });
  return slots;
}

export function confirmCopy(kind: "result" | "workout"): string {
  if (kind === "result") return "Confirm this result before the plan changes.";
  return "Confirm this workout before the plan changes.";
}

export function watchlessSummary(saved: { mark?: string; text?: string } | null | undefined): string {
  const parts = ["Completed"];
  const label = saved?.mark ? OUTCOME[saved.mark] : "";
  if (label) parts.push(label);
  const text = (saved?.text || "").trim();
  if (text) parts.push(text);
  return parts.join(" · ");
}

export function needsOutcome(quality: boolean, choice: string): string {
  if (!quality) return "";
  if (choice === "Behind" || choice === "On track" || choice === "Ahead") return "";
  return "Choose behind, on target, or ahead.";
}
