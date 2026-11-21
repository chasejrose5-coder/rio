/**
 * Daily core circuits for any runner.
 * The list and the day are rules. A date and the plan pick the circuit.
 * Hard days are about 8 minutes. Easy and rest days are 12–15 minutes.
 * Race day and the day before have none.
 */

import { classifyDay, weekStart, type DayKind, type StretchSession } from "./stretch-content.ts";

export type CoreCategory = "anti-extension" | "anti-rotation" | "lateral" | "flexion" | "running";

export const CORE_DISCLAIMER = "Not medical advice. See a professional if it hurts.";

export const CATEGORY_LABEL: Record<CoreCategory, string> = {
  "anti-extension": "Anti-extension",
  "anti-rotation": "Anti-rotation",
  lateral: "Lateral",
  flexion: "Flexion and hips",
  running: "Running-specific",
};

export const CATEGORIES: readonly CoreCategory[] = [
  "anti-extension",
  "anti-rotation",
  "lateral",
  "flexion",
  "running",
];

export type CoreExercise = {
  id: string;
  name: string;
  category: CoreCategory;
  dose: string;
  /** Work plus the move to the next exercise. The generator uses this, not the dose text. */
  seconds: number;
  howTo: string;
};

type Row = [string, string, CoreCategory, string, number, string];

const ROWS: readonly Row[] = [
  ["plank", "Plank", "anti-extension", "40 s", 80, "Forearms under the shoulders, body in one line, and hold without letting the hips sag."],
  ["dead-bug", "Dead bug", "anti-extension", "6 each side", 80, "Lie on your back with the arms and knees up, reach the opposite arm and leg away, and keep the low back gently down."],
  ["ab-rollout", "Ab rollout", "anti-extension", "6", 80, "From the knees, roll a wheel or sliders forward only as far as the ribs stay down, then pull back."],
  ["body-saw", "Body saw", "anti-extension", "8", 80, "From a forearm plank, slide the feet back a few inches and pull them back in, keeping the hips level."],

  ["pallof", "Pallof press", "anti-rotation", "8 each side", 80, "Hold a band at the chest, press it straight out, and resist the twist back to the anchor."],
  ["bird-dog", "Bird dog", "anti-rotation", "6 each side", 80, "On hands and knees, reach the opposite arm and leg long and keep the hips still."],
  ["renegade", "Renegade hold", "anti-rotation", "20 s each side", 80, "In a high plank, lift one hand a few inches and hold without rocking the hips."],
  ["chops", "Banded chops", "anti-rotation", "8 each side", 80, "Pull a high band down across the body to the opposite hip, and let the hips stay square."],

  ["side-plank", "Side plank", "lateral", "20 s each side", 80, "Lie on one forearm with the body straight and hold. Bend the knees if you need to."],
  ["side-lift", "Side plank leg lift", "lateral", "6 each side", 80, "From the side plank, lift the top leg a short way and set it down without dropping the hips."],
  ["copenhagen", "Copenhagen plank", "lateral", "12 s each side", 80, "Side plank with the top leg on a bench. Use the knee if the straight leg is too much."],
  ["suitcase", "Suitcase carry", "lateral", "20 m each side", 80, "Hold a weight in one hand and walk tall, without leaning away from the weight."],

  ["hanging", "Hanging knee raise", "flexion", "6", 80, "Hang from a bar, bring the knees toward the chest, and lower without swinging."],
  ["v-up", "V-ups", "flexion", "6", 80, "Lie long, lift the hands and feet to meet, and lower with control. Bend the knees if the back grabs."],
  ["reverse-crunch", "Reverse crunch", "flexion", "8", 80, "Lie on your back, curl the knees toward the chest, and lift the hips a short way off the floor."],
  ["hollow", "Hollow hold", "flexion", "20 s", 80, "Lie on your back, press the low back down, and hold the arms and legs long just off the floor."],

  ["balance-reach", "Single-leg balance reach", "running", "6 each side", 80, "Stand on one leg and reach the free foot back, then return, with the hips square."],
  ["march-bridge", "Marching bridge", "running", "6 each side", 80, "Lift the hips into a bridge and march one knee up at a time, keeping the hips level."],
  ["knee-drive", "Banded standing knee drive", "running", "8 each side", 80, "Anchor a band behind you, stand tall, and drive one knee up against the band."],
  ["plank-drive", "Plank knee drive", "running", "8 each side", 80, "From a high plank, drive one knee toward the chest and switch, without letting the hips bounce."],
];

export const CORE_EXERCISES: readonly CoreExercise[] = ROWS.map(([id, name, category, dose, seconds, howTo]) => ({
  id,
  name,
  category,
  dose,
  seconds,
  howTo,
}));

const byCategory = new Map<CoreCategory, CoreExercise[]>();
for (const category of CATEGORIES) byCategory.set(category, []);
for (const exercise of CORE_EXERCISES) byCategory.get(exercise.category)?.push(exercise);

export type CoreCircuit = {
  date: string;
  kind: DayKind;
  seconds: number;
  label: string;
  exercises: CoreExercise[];
};

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

function daysSinceEpoch(iso: string): number {
  const match = ISO.exec(iso);
  if (!match) return 0;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return 0;
  return Math.floor(date.getTime() / 86400000);
}

function shiftDays(iso: string, days: number): string {
  const match = ISO.exec(iso);
  if (!match) return iso;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return iso;
  date.setUTCDate(date.getUTCDate() + days);
  const nextMonth = String(date.getUTCMonth() + 1).padStart(2, "0");
  const nextDay = String(date.getUTCDate()).padStart(2, "0");
  return `${date.getUTCFullYear()}-${nextMonth}-${nextDay}`;
}

function sessionOn(date: string, sessions: readonly StretchSession[]): StretchSession | null {
  for (const session of sessions) {
    if (session.date === date) return session;
  }
  return null;
}

function kindOn(date: string, sessions: readonly StretchSession[]): DayKind {
  const session = sessionOn(date, sessions);
  if (!session) return "rest";
  return classifyDay(date, session);
}

function blocked(date: string, sessions: readonly StretchSession[]): boolean {
  if (kindOn(date, sessions) === "race") return true;
  return kindOn(shiftDays(date, 1), sessions) === "race";
}

function bounds(kind: DayKind): { min: number; target: number; max: number } {
  if (kind === "quality" || kind === "long") return { min: 7 * 60, target: 8 * 60, max: 9 * 60 };
  return { min: 12 * 60, target: 14 * 60, max: 15 * 60 };
}

export function minuteLabel(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  return `About ${minutes} min`;
}

/** One circuit per calendar day in the Sunday week, so the categories stay balanced. */
export function weekCircuits(date: string, sessions: readonly StretchSession[] = []): Map<string, CoreCircuit | null> {
  const start = weekStart(date);
  const week = Math.floor(daysSinceEpoch(start) / 7);
  const cursor = CATEGORIES.map((category) => week % (byCategory.get(category)?.length || 1));
  const used = CATEGORIES.map(() => 0);
  const out = new Map<string, CoreCircuit | null>();
  for (let offset = 0; offset < 7; offset += 1) {
    const day = shiftDays(start, offset);
    if (blocked(day, sessions)) {
      out.set(day, null);
      continue;
    }
    const kind = kindOn(day, sessions);
    const limit = bounds(kind);
    const picks: CoreExercise[] = [];
    let total = 0;
    let guard = 0;
    while (total < limit.target && guard < 40) {
      guard += 1;
      const order = CATEGORIES.map((category, index) => ({
        index,
        used: used[index] ?? 0,
        tie: (week + offset + index) % CATEGORIES.length,
      }));
      order.sort((left, right) => left.used - right.used || left.tie - right.tie);
      const index = order[0]?.index ?? 0;
      const list = byCategory.get(CATEGORIES[index] ?? "anti-extension") ?? [];
      const exercise = list[(cursor[index] ?? 0) % list.length];
      if (!exercise) break;
      if (total > 0 && total + exercise.seconds > limit.max) break;
      if (total >= limit.min && total + exercise.seconds > limit.max) break;
      picks.push(exercise);
      total += exercise.seconds;
      used[index] = (used[index] ?? 0) + 1;
      cursor[index] = (cursor[index] ?? 0) + 1;
    }
    out.set(day, { date: day, kind, seconds: total, label: minuteLabel(total), exercises: picks });
  }
  return out;
}

export function circuitFor(date: string, sessions: readonly StretchSession[] = []): CoreCircuit | null {
  return weekCircuits(date, sessions).get(date) ?? null;
}
