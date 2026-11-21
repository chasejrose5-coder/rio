/**
 * Injury-prevention library for any runner.
 * Names, doses, and how-tos live here. They are not stored in the database.
 * Which days and which level are rules: a date and the saved areas decide them.
 * Level dates stay in step with engines/injury.py.
 */

import { classifyDay, weekStart, type StretchSession } from "./stretch-content.ts";

export type LevelName = "easy" | "medium" | "hard";

export const LEVELS = ["easy", "medium", "hard"] as const;

export const INJURY_DISCLAIMER = "Not medical advice. See a professional if it hurts.";

export const BONE_MESSAGE = "Walk-run return only. See a doctor first.";

export type InjuryExercise = {
  id: string;
  name: string;
  areaId: string;
  /** Empty means every level. Otherwise the exercise is only for these levels. */
  stages: readonly LevelName[];
  doses: Record<LevelName, string>;
  howTo: string;
};

export type InjuryArea = {
  id: string;
  group: string;
  label: string;
  bone?: boolean;
};

export type AreaLevel = {
  areaId: string;
  level: LevelName;
};

export type DosedExercise = {
  exercise: InjuryExercise;
  dose: string;
};

export type DayBlock = {
  id: string;
  title: string;
  level: LevelName | null;
  exercises: DosedExercise[];
  boneMessage?: string;
};

const DOSE = (easy: string, medium: string, hard: string): Record<LevelName, string> => ({ easy, medium, hard });

type Row = [string, string, string, readonly LevelName[], string, string, string, string];

const ROWS: readonly Row[] = [
  ["pf-towel", "Towel scrunches", "plantar-fascia", [], "1×10", "2×12", "3×15", "Sit with a towel flat under the foot and scrunch it toward you with the toes, then reset."],
  ["pf-short-foot", "Short-foot holds", "plantar-fascia", [], "3×10 s", "4×15 s", "5×20 s", "Standing, shorten the arch by drawing the ball of the foot toward the heel without curling the toes, and hold."],
  ["pf-towel-raise", "Single-leg calf raise on a towel roll", "plantar-fascia", [], "1×8 each side", "2×10 each side", "3×12 each side", "Stand on one leg with the toes on a rolled towel, rise onto the ball of the foot, and lower slowly."],

  ["an-balance", "Single-leg balance", "ankle-sprain", [], "2×20 s each side", "3×30 s each side", "3×45 s each side", "Stand on one leg with a soft knee and level hips, using a wall for a fingertip if you need it."],
  ["an-eyes", "Eyes-closed balance", "ankle-sprain", [], "2×10 s each side", "3×15 s each side", "3×20 s each side", "From the same single-leg stance, close the eyes, and open them to reset if you tip."],
  ["an-4way", "Banded 4-way ankle", "ankle-sprain", [], "1×8 each way", "2×10 each way", "3×12 each way", "With a band around the forefoot, move the foot up, down, in, and out while the knee stays still."],
  ["an-hop", "Hop-and-stick", "ankle-sprain", [], "1×6 each side", "2×8 each side", "3×8 each side", "Hop a short distance and stick the landing on one leg, quiet and still, with the knee over the foot."],

  ["pe-eversion", "Banded eversion", "peroneal", [], "2×10 each side", "3×12 each side", "3×15 each side", "Sit with a band around the forefoot and turn the sole outward, then return slowly."],
  ["pe-hops", "Lateral line hops", "peroneal", [], "1×8 each side", "2×10 each side", "3×10 each side", "Hop sideways along a line and stick each landing with the knee tracking over the foot."],

  ["ac-iso", "Isometric calf-raise holds", "achilles", ["easy"], "3×20 s", "4×30 s", "5×45 s", "Rise onto the balls of both feet and hold, with a wall for balance. Stop if the tendon pinches."],
  ["ac-double", "Double-leg straight-leg calf raises", "achilles", ["medium"], "2×8", "3×10", "3×15", "With the knees straight, rise onto the balls of both feet and lower with control."],
  ["ac-single", "Single-leg straight-leg calf raises", "achilles", ["medium"], "2×6 each side", "2×8 each side", "3×10 each side", "Rise on one leg with the knee straight, and take a full three seconds to lower."],
  ["ac-eccentric", "Slow eccentric heel drops", "achilles", ["medium"], "2×6 each side", "3×8 each side", "3×12 each side", "Rise on both feet, shift onto one leg, and lower that heel below a step over three seconds."],
  ["ac-bent", "Weighted bent-knee calf raises", "achilles", ["hard"], "2×8", "3×10", "3×12", "Hold a light weight, bend the knees a little, rise onto the toes, and lower slowly."],
  ["ac-pogo", "Pogo hops", "achilles", ["hard"], "2×10", "3×15", "3×20", "Small quick hops on the balls of the feet, quiet and springy, staying tall."],

  ["so-seated", "Seated calf raises", "soleus", [], "2×10", "3×12", "3×15", "Sit with the knees bent and a weight on the thighs, then rise onto the balls of the feet."],
  ["so-wall", "Weighted wall sit on toes", "soleus", [], "2×20 s", "3×30 s", "3×40 s", "Hold a wall sit with the heels lifted and a light weight in the lap, knees over the toes."],

  ["sh-tib-wall", "Tibialis wall raises", "shins", [], "2×8", "3×10", "3×15", "Stand with the back on a wall and the heels a step out, and lift the toes toward the shins."],
  ["sh-heel-walk", "Heel walks", "shins", [], "20 m", "2×20 m", "3×20 m", "Walk on the heels with the toes lifted and the steps short."],
  ["sh-band", "Banded dorsiflexion", "shins", [], "2×10 each side", "3×12 each side", "3×15 each side", "Anchor a band over the foot and draw the toes toward the shin against the band."],
  ["sh-pogo", "Gradual pogos", "shins", [], "2×8", "2×12", "3×12", "Tiny hops on the balls of the feet. Add a few only when the shins stay quiet."],

  ["pa-spanish", "Spanish squat holds", "patellar", ["easy"], "3×20 s", "4×30 s", "5×45 s", "Loop a band behind the knees, sit back until the shins stay upright, and hold."],
  ["pa-decline", "Slow decline squats", "patellar", ["medium"], "2×6", "3×8", "3×10", "With the heels on a slant, sit down over three seconds and stand without bouncing."],
  ["pa-step", "Step-downs", "patellar", ["medium", "hard"], "2×6 each side", "3×8 each side", "3×10 each side", "Stand on a low step, lower the free heel to the floor, and press back up."],
  ["pa-jump", "Step-down jumps", "patellar", ["hard"], "1×4 each side", "2×5 each side", "2×6 each side", "From the same step, hop down and stick the landing with the knee over the foot. Skip these if the tendon is sore."],

  ["pfps-wall-sit", "Wall sits", "pfps", [], "2×20 s", "3×30 s", "3×45 s", "Slide down a wall until the thighs are near parallel and hold, with the knees over the feet."],
  ["pfps-step", "Step-ups", "pfps", [], "2×8 each side", "3×10 each side", "3×12 each side", "Step up onto a low box, stand tall, and lower with control."],
  ["pfps-band", "Lateral band walks", "pfps", [], "2×8 each side", "3×10 each side", "3×12 each side", "With a band above the knees, sit into a small squat and step sideways without letting the knees cave."],
  ["pfps-box", "Single-leg box squats", "pfps", [], "2×6 each side", "3×8 each side", "3×8 each side", "Sit back to a box on one leg, tap it, and stand without dropping the hip."],

  ["it-side-plank", "Side planks", "it-band", [], "2×15 s each side", "3×25 s each side", "3×35 s each side", "Lie on one forearm in a straight line and hold. Bend the knees if the full plank is too much."],
  ["it-clamshell", "Clamshells", "it-band", [], "2×10 each side", "3×12 each side", "3×15 each side", "Lie on your side with the knees bent and the feet together, and lift the top knee without rolling the hips back."],
  ["it-rdl", "Single-leg RDL", "it-band", [], "2×6 each side", "3×8 each side", "3×10 each side", "Hinge on one leg, reach the other leg back, and keep the hips square as you stand."],
  ["it-step", "Lateral step-downs", "it-band", [], "2×6 each side", "3×8 each side", "3×10 each side", "Stand sideways on a step, lower the free foot by bending the standing knee, and press up."],

  ["gm-clamshell", "Clamshells", "glute-med", [], "2×10 each side", "3×12 each side", "3×15 each side", "Lie on your side with the knees bent and the feet together, and lift the top knee without rolling the hips back."],
  ["gm-side-leg", "Side-lying leg raises", "glute-med", [], "2×8 each side", "3×10 each side", "3×12 each side", "Lie on your side with the top leg straight and lift it a short way, keeping the hips stacked."],
  ["gm-monster", "Monster walks", "glute-med", [], "2×8 each side", "3×10 each side", "3×12 each side", "Band above the knees, sit into a quarter squat, and step forward and out without the knees caving."],
  ["gm-bridge", "Single-leg bridges", "glute-med", [], "2×6 each side", "3×8 each side", "3×10 each side", "Lie on your back, lift the hips, and hold one leg out while the other heel drives the floor."],

  ["hf-knee-drive", "Banded knee drives", "hip-flexors", [], "2×8 each side", "3×10 each side", "3×12 each side", "Anchor a band behind you, stand tall, and drive one knee up against the band."],
  ["hf-march", "Standing march", "hip-flexors", [], "2×10 each side", "3×12 each side", "3×15 each side", "March in place, lifting the knee to hip height and staying tall."],
  ["hf-couch", "Couch stretch", "hip-flexors", [], "2×20 s each side", "2×30 s each side", "2×45 s each side", "Kneel with the back shin up a couch or bench and the front foot on the floor, and stay tall."],

  ["ad-copenhagen-short", "Copenhagen plank, short lever", "adductors", ["easy"], "2×10 s each side", "3×15 s each side", "3×20 s each side", "Side plank with the top leg on a bench near the knee, and hold the bottom leg just off the floor."],
  ["ad-copenhagen-long", "Copenhagen plank, long lever", "adductors", ["medium", "hard"], "2×8 s each side", "2×12 s each side", "3×15 s each side", "Same side plank, with the top foot on the bench so the leg is straighter. Come down if the groin grabs."],
  ["ad-squeeze", "Adductor squeeze holds", "adductors", [], "3×15 s", "4×20 s", "4×25 s", "Sit or lie with a ball or pillow between the knees and squeeze, then ease off."],
  ["ad-lunge", "Side lunges", "adductors", [], "2×6 each side", "3×8 each side", "3×8 each side", "Step wide, sit toward that foot, and keep the other leg straight as you push back."],

  ["hh-iso", "Isometric bridge holds", "high-hamstring", ["easy"], "3×20 s", "4×25 s", "4×30 s", "Lie on your back, lift the hips, and hold. Press through the heels and keep the ribs down."],
  ["hh-single", "Single-leg bridges", "high-hamstring", ["medium"], "2×6 each side", "3×8 each side", "3×10 each side", "From the bridge, extend one leg and hold the hips level while the other heel works."],
  ["hh-rdl", "Romanian deadlifts", "high-hamstring", ["medium", "hard"], "2×6", "3×8", "3×8", "Hinge with a soft knee until the hamstrings load, then stand tall without rounding the back."],
  ["hh-slide", "Sliding leg curls", "high-hamstring", ["hard"], "2×6", "3×8", "3×10", "Lie on your back with the heels on sliders, lift the hips, and curl the heels toward you."],

  ["hs-assisted", "Assisted Nordics", "hamstring-strain", ["easy", "medium"], "2×3", "3×4", "3×5", "Kneel with the feet held, lower slowly, and push back up with your hands."],
  ["hs-nordic", "Nordics", "hamstring-strain", ["hard"], "2×3", "3×4", "3×5", "Same kneeling lower, with less help from the hands. Stop the set if the hamstring grabs."],
  ["hs-askip", "A-skips", "hamstring-strain", [], "2×15 m", "3×20 m", "3×20 m", "Skip forward, lifting the knee and snapping the foot down under the hip."],
  ["hs-bound", "Straight-leg bounds", "hamstring-strain", ["medium", "hard"], "2×15 m", "3×20 m", "3×20 m", "Bound forward with a straighter knee, reaching from the hip, and stay tall."],

  ["lb-bird-dog", "Bird dogs", "low-back", [], "2×6 each side", "3×8 each side", "3×8 each side", "On hands and knees, reach the opposite arm and leg long, and keep the hips still."],
  ["lb-dead-bug", "Dead bugs", "low-back", [], "2×6 each side", "3×8 each side", "3×8 each side", "Lie on your back with the arms and knees up, reach the opposite arm and leg away, and keep the low back gently down."],
  ["lb-curl", "McGill curl-ups", "low-back", [], "2×6", "3×6", "3×8", "One knee bent, hands under the low back, and curl the head and shoulders a short way off the floor."],
  ["lb-side-plank", "Side planks", "low-back", [], "2×15 s each side", "3×20 s each side", "3×30 s each side", "Lie on one forearm with the body straight and hold. Bend the knees if you need to."],
];

export const EXERCISES: readonly InjuryExercise[] = ROWS.map(([id, name, areaId, stages, easy, medium, hard, howTo]) => ({
  id,
  name,
  areaId,
  stages,
  doses: DOSE(easy, medium, hard),
  howTo,
}));

const byId = new Map(EXERCISES.map((exercise) => [exercise.id, exercise]));

export function exerciseById(id: string): InjuryExercise | undefined {
  return byId.get(id);
}

export const AREAS: readonly InjuryArea[] = [
  { id: "plantar-fascia", group: "Feet & ankles", label: "Plantar fascia" },
  { id: "ankle-sprain", group: "Feet & ankles", label: "Ankle sprain" },
  { id: "peroneal", group: "Feet & ankles", label: "Peroneal tendons" },
  { id: "achilles", group: "Achilles & soleus", label: "Achilles tendon" },
  { id: "soleus", group: "Achilles & soleus", label: "Soleus" },
  { id: "shins", group: "Shins", label: "Shins / tibial stress" },
  { id: "bone-stress", group: "Shins", label: "Bone stress", bone: true },
  { id: "patellar", group: "Knees", label: "Patellar tendon" },
  { id: "pfps", group: "Knees", label: "Patellofemoral pain" },
  { id: "it-band", group: "Knees", label: "IT band" },
  { id: "glute-med", group: "Hips & glutes", label: "Glute med" },
  { id: "hip-flexors", group: "Hips & glutes", label: "Hip flexors" },
  { id: "adductors", group: "Hips & glutes", label: "Adductors / groin" },
  { id: "high-hamstring", group: "Hamstrings", label: "High hamstring tendon" },
  { id: "hamstring-strain", group: "Hamstrings", label: "Hamstring strain" },
  { id: "low-back", group: "Low back", label: "Low back" },
];

const areaMap = new Map(AREAS.map((area) => [area.id, area]));

export function areaById(id: string): InjuryArea | undefined {
  return areaMap.get(id);
}

export const GROUPS: readonly string[] = [...new Set(AREAS.map((area) => area.group))];

/** Foundational easy doses. The week rotates which four are used. */
export const GENERAL_IDS: readonly string[] = [
  "pf-short-foot",
  "an-balance",
  "ac-iso",
  "sh-tib-wall",
  "pfps-wall-sit",
  "gm-clamshell",
  "gm-side-leg",
  "lb-dead-bug",
  "lb-bird-dog",
  "hf-knee-drive",
  "ad-squeeze",
  "lb-side-plank",
];

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

export function daysBetween(start: string, end: string): number {
  if (!ISO.test(start) || !ISO.test(end)) return 0;
  return daysSinceEpoch(end) - daysSinceEpoch(start);
}

/** Same 14-day steps as engines/injury.py level_index. */
export function levelOn(stored: number, anchorOn: string, on: string): LevelName {
  if (stored !== 0 && stored !== 1 && stored !== 2) return "easy";
  const days = daysBetween(anchorOn, on);
  const periods = days < 0 ? 0 : Math.floor(days / 14);
  return LEVELS[Math.min(2, stored + periods)];
}

function weekIndex(date: string): number {
  return Math.floor(daysSinceEpoch(weekStart(date)) / 7);
}

function weekdayOffset(date: string): number {
  const start = weekStart(date);
  const delta = daysSinceEpoch(date) - daysSinceEpoch(start);
  if (delta < 0 || delta > 6) return -1;
  return delta;
}

/** Even calendar weeks: Monday, Wednesday, Friday. Odd weeks: Monday and Thursday. */
export function generalOffsets(date: string): readonly number[] {
  return weekIndex(date) % 2 === 0 ? [1, 3, 5] : [1, 4];
}

/** Tuesday, Thursday, and Saturday. */
export const REBUILDING_OFFSETS: readonly number[] = [2, 4, 6];

function sessionOn(date: string, sessions: readonly StretchSession[]): StretchSession | null {
  for (const session of sessions) {
    if (session.date === date) return session;
  }
  return null;
}

export function isRaceOrEve(date: string, sessions: readonly StretchSession[]): boolean {
  const today = sessionOn(date, sessions);
  if (today && classifyDay(date, today) === "race") return true;
  const nextDate = shiftDays(date, 1);
  const next = sessionOn(nextDate, sessions);
  return Boolean(next && classifyDay(nextDate, next) === "race");
}

export function isGeneralDay(date: string, sessions: readonly StretchSession[] = []): boolean {
  if (isRaceOrEve(date, sessions)) return false;
  return generalOffsets(date).includes(weekdayOffset(date));
}

export function isRebuildingDay(date: string, sessions: readonly StretchSession[] = []): boolean {
  if (isRaceOrEve(date, sessions)) return false;
  return REBUILDING_OFFSETS.includes(weekdayOffset(date));
}

export function generalExerciseIds(date: string): string[] {
  const slot = generalOffsets(date).indexOf(weekdayOffset(date));
  if (slot < 0) return [];
  const start = (weekIndex(date) * 3 + slot * 4) % GENERAL_IDS.length;
  return [0, 1, 2, 3].map((step) => GENERAL_IDS[(start + step) % GENERAL_IDS.length]);
}

export function exercisesFor(areaId: string, level: LevelName): DosedExercise[] {
  return EXERCISES.filter((exercise) => exercise.areaId === areaId && (exercise.stages.length === 0 || exercise.stages.includes(level))).map(
    (exercise) => ({ exercise, dose: exercise.doses[level] }),
  );
}

export function dayBlocks(date: string, sessions: readonly StretchSession[], areas: readonly AreaLevel[]): DayBlock[] {
  if (isRaceOrEve(date, sessions)) return [];
  const blocks: DayBlock[] = [];
  const rebuilding = isRebuildingDay(date, sessions) ? areas : [];
  const rebuildingIds = new Set(rebuilding.map((area) => area.areaId));
  if (isGeneralDay(date, sessions)) {
    const exercises = generalExerciseIds(date)
      .map((id) => exerciseById(id))
      .filter((exercise): exercise is InjuryExercise => Boolean(exercise))
      .filter((exercise) => !rebuildingIds.has(exercise.areaId))
      .map((exercise) => ({ exercise, dose: exercise.doses.easy }));
    if (exercises.length) {
      blocks.push({ id: "general", title: "General prevention", level: "easy", exercises });
    }
  }
  if (!isRebuildingDay(date, sessions)) return blocks;
  for (const area of AREAS) {
    const selected = areas.find((item) => item.areaId === area.id);
    if (!selected) continue;
    if (area.bone) {
      blocks.push({ id: area.id, title: area.label, level: null, exercises: [], boneMessage: BONE_MESSAGE });
      continue;
    }
    blocks.push({
      id: area.id,
      title: area.label,
      level: selected.level,
      exercises: exercisesFor(area.id, selected.level),
    });
  }
  return blocks;
}
