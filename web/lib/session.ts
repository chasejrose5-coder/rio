/** Session page copy and the result boxes. Pace stays on GET /sessions. */

export const PREP = [
  {
    title: "Pre-warm-up",
    lines: ["1 × 800 m easy"],
  },
  {
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
  },
  {
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
  },
  {
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
  },
] as const;

const OUTCOME: Record<string, string> = {
  not_hitting: "Behind",
  on_track: "On target",
  smashing: "Ahead",
};

export function sessionHref(next: string | null | undefined): string {
  if (typeof next === "string" && /^\d{4}-\d{2}-\d{2}$/.test(next)) return `/session?date=${next}`;
  return "/session";
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
  if (choice === "Behind" || choice === "On target" || choice === "Ahead") return "";
  return "Choose behind, on target, or ahead.";
}
