/**
 * Foam rolling for any runner.
 * A hard day and a long run get a short routine. Other days keep it optional.
 * The order rotates so the same area is not always first.
 */

import { classifyDay, weekStart, type DayKind, type StretchSession } from "./stretch-content.ts";

export const FOAM_DISCLAIMER = "Not medical advice. See a professional if it hurts.";

export type FoamArea = {
  id: string;
  name: string;
  howTo: string;
};

export const FOAM_AREAS: readonly FoamArea[] = [
  { id: "calves", name: "Calves", howTo: "Roll slowly from the Achilles toward the knee. Ease off any spot that feels sharp." },
  { id: "quads", name: "Quads", howTo: "Lie face down with the roller under one thigh and roll from the hip toward the knee." },
  { id: "hamstrings", name: "Hamstrings", howTo: "Sit with the roller under one thigh and roll from the knee toward the hip, keeping the foot relaxed." },
  { id: "it-band", name: "IT band", howTo: "Lie on your side with the roller under the outer thigh and roll slowly. Skip a spot that bites." },
  { id: "glutes", name: "Glutes", howTo: "Sit on the roller, cross one ankle over the other knee, and roll the glute of the crossed leg." },
  { id: "hips", name: "Hips and adductors", howTo: "Lie face down with the roller in the inner thigh and roll a short path, staying off the knee." },
  { id: "feet", name: "Feet", howTo: "Roll a ball under the arch from the heel toward the ball of the foot. Use enough pressure to feel it, and ease off if it bites." },
];

export type FoamStop = FoamArea & { seconds: number };

export type FoamRoutine = {
  date: string;
  kind: DayKind;
  required: boolean;
  label: string;
  seconds: number;
  areas: FoamStop[];
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

export function clock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes === 0) return `${rest} s`;
  if (rest === 0) return `${minutes} min`;
  return `${minutes} min ${rest} s`;
}

export function foamRoutine(date: string, sessions: readonly StretchSession[] = []): FoamRoutine {
  const kind = kindOn(date, sessions);
  const required = kind === "quality" || kind === "long";
  const seconds = required ? 60 : 30;
  const start = weekStart(date);
  const week = Math.floor(daysSinceEpoch(start) / 7);
  const offset = daysSinceEpoch(date) - daysSinceEpoch(start);
  const shift = (week + Math.max(0, offset)) % FOAM_AREAS.length;
  const ordered = [...FOAM_AREAS.slice(shift), ...FOAM_AREAS.slice(0, shift)];
  const areas = ordered.map((area) => ({ ...area, seconds }));
  const total = seconds * areas.length;
  return {
    date,
    kind,
    required,
    seconds: total,
    label: required ? `After this workout · ${clock(total)}` : `Optional · ${clock(total)}`,
    areas,
  };
}
