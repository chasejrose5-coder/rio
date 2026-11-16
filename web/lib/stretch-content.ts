/**
 * Stretching library for any runner.
 * Names, doses, and how-tos live here. They are not stored in the database.
 */

export type StretchType = "D" | "S";

export type Exercise = {
  id: number;
  name: string;
  area: string;
  type: StretchType;
  dose: string;
  howTo: string;
};

export type Routine = {
  id: string;
  name: string;
  minutes: number;
  exerciseIds: readonly number[];
};

export type Region = {
  id: string;
  label: string;
  /** Exercises added while a mild or moderate spot is active. */
  extraIds: readonly number[];
  color: string;
};

const ROWS: readonly [number, string, string, StretchType, string, string][] = [
  [1, "Ankle circles", "Feet & ankles", "D", "10 each way per foot", "Sit or stand on one leg and draw a slow circle with the other foot, ten one way and ten the other. Keep the knee still so the circle comes from the ankle."],
  [2, "Toe yoga", "Feet & ankles", "D", "10 reps", "Lift the big toe while the smaller toes stay down, then switch, for ten reps on each foot. Spread the toes instead of gripping the floor."],
  [3, "Plantar fascia ball roll", "Feet & ankles", "S", "60 s per foot", "Roll a ball under the arch from the heel toward the ball of the foot for about a minute, then switch. Use enough pressure to feel the arch, and ease off if it bites."],
  [4, "Kneeling toe stretch", "Feet & ankles", "S", "30-45 s", "Kneel with the toes tucked under and sit the hips back toward the heels for 30 to 45 seconds. Keep the weight even across both feet."],
  [5, "Wall calf stretch, straight knee", "Calves & Achilles", "S", "30 s per side", "Face a wall with one foot back and press that heel down, knee straight, for 30 seconds each side. Point the back foot straight at the wall."],
  [6, "Wall calf stretch, bent knee/soleus", "Calves & Achilles", "S", "30 s per side", "From the same wall stance, bend the back knee a little and keep the heel down for 30 seconds each side. Let the stretch sit lower, near the Achilles."],
  [7, "Eccentric heel drops off a step", "Calves & Achilles", "D", "2x10 per side", "Stand on a step with the heels off the edge, rise up, then lower the heel slowly below the step for two sets of ten each side. Hold a rail so the lowering stays in your control."],
  [8, "Downward dog calf pedal", "Calves & Achilles", "D", "10 per side", "Lift the hips into an inverted V and pedal the heels, pressing one toward the floor at a time for ten each side. Keep the hands planted and the hips high."],
  [9, "Kneeling shin stretch", "Shins", "S", "30 s", "Kneel and sit on the heels with the tops of the feet on the floor for about 30 seconds. Sit tall instead of collapsing onto the toes."],
  [10, "Toe walks and heel walks", "Shins", "D", "20 m each", "Walk 20 metres on the toes, then 20 metres on the heels, with short steps. Stay tall and point the feet forward."],
  [11, "Seated tibialis raises", "Shins", "D", "15 reps", "Sit with the heels down and lift the toes toward the shins for 15 slow reps. Move at the ankle and leave the knees quiet."],
  [12, "Leg swings front-back", "Hamstrings", "D", "15 per side", "Hold a wall and swing one leg forward and back like a pendulum for 15 swings each side. Stay tall and let the swinging leg stay loose."],
  [13, "Standing hamstring sweep", "Hamstrings", "D", "10 per side", "Stand on one leg and sweep the other foot forward and back along the floor for 10 each side. Hinge a little at the hips and keep the standing knee soft."],
  [14, "Lying strap hamstring stretch", "Hamstrings", "S", "30-45 s per side", "Lie on your back, loop a strap or belt around one foot, and raise that leg until the back of the thigh stretches for 30 to 45 seconds each side. Keep the other leg long on the floor and the hips level."],
  [15, "Seated forward fold", "Hamstrings", "S", "45 s", "Sit with the legs straight and fold from the hips toward the thighs for about 45 seconds. Lead with the chest rather than rounding through the neck."],
  [16, "Standing quad stretch", "Quads", "S", "30 s per side", "Stand on one leg and bring the other heel toward the glute for 30 seconds each side. Keep the knees close and the hips pointing forward."],
  [17, "Butt kicks", "Quads", "D", "20 m", "Jog 20 metres while kicking the heels up toward the glutes. Keep the steps light and the knees pointing down."],
  [18, "Side-lying quad stretch", "Quads", "S", "30 s per side", "Lie on one side, bend the top knee, and hold the foot behind you for 30 seconds each side. Keep the thigh in line with the body so it does not drift forward."],
  [19, "Kneeling hip flexor lunge with arm reach", "Hip flexors", "S", "30-45 s per side", "Kneel in a lunge and reach the same-side arm overhead for 30 to 45 seconds each side. Tuck the pelvis slightly so the stretch stays in the front of the hip."],
  [20, "Couch stretch", "Hip flexors", "S", "45-60 s per side", "Kneel with the back shin up a couch or bench and the front foot on the floor for 45 to 60 seconds each side. Stay tall and keep the front knee over the ankle."],
  [21, "Walking lunge with twist", "Hip flexors", "D", "8 per side", "Step into a lunge and turn the chest toward the front leg, then switch, for eight each side. The front knee stays over the foot."],
  [22, "Figure-4 stretch on back", "Glutes & piriformis", "S", "30-45 s per side", "Lie on your back, cross one ankle over the opposite knee, and draw the uncrossed thigh in for 30 to 45 seconds each side. Keep the head down and the hips on the floor."],
  [23, "Pigeon pose", "Glutes & piriformis", "S", "45-60 s per side", "From all fours, bring one shin across in front and extend the other leg back for 45 to 60 seconds each side. Square the hips as well as you can and support yourself on your hands."],
  [24, "Glute bridges", "Glutes & piriformis", "D", "2x12", "Lie on your back with the feet flat and lift the hips until the body lines up from knees to shoulders, two sets of twelve. Press through the heels and pause at the top."],
  [25, "Clamshells", "Glutes & piriformis", "D", "15 per side", "Lie on one side with the knees bent and the feet together, then lift the top knee for 15 each side. Keep the pelvis still so the hip does the work."],
  [26, "Leg swings side-to-side", "Adductors", "D", "15 per side", "Hold a wall and swing one leg across the body and out to the side for 15 each side. Stand tall and keep the swing smooth."],
  [27, "Butterfly stretch", "Adductors", "S", "45 s", "Sit with the soles of the feet together and let the knees fall open for about 45 seconds. If you fold, hinge from the hips and keep the spine long."],
  [28, "Frog stretch", "Adductors", "S", "45-60 s", "From hands and knees, widen the knees and sit the hips back with the feet turned out for 45 to 60 seconds. Keep some weight in the hands so you can ease out."],
  [29, "Lateral lunge", "Adductors", "D", "8 per side", "Step wide to one side, bend that knee, and keep the other leg straight, then switch, for eight each side. The bent knee tracks over the foot."],
  [30, "Standing cross-over side bend", "IT band & outer hip", "S", "30 s per side", "Cross one leg in front of the other and reach the opposite arm overhead, bending away from the back leg, for 30 seconds each side. Stay long through the side of the hip."],
  [31, "Foam roll outer thigh/TFL", "IT band & outer hip", "S", "60 s per side", "Lie on one side with a roller under the outer thigh, just below the hip, and roll slowly for about a minute each side. Support yourself on your arms and skip any spot that feels sharp."],
  [32, "Fire hydrants", "IT band & outer hip", "D", "12 per side", "On hands and knees, lift one knee out to the side and lower it for 12 each side. Keep the hips level and the supporting knee under the hip."],
  [33, "Cat-cow", "Lower back & core", "D", "10 slow reps", "On hands and knees, round the back up and then let the chest and belly sink, for ten slow reps. Move one part of the spine at a time, with the hands under the shoulders."],
  [34, "Child's pose", "Lower back & core", "S", "60 s", "Sit the hips toward the heels and reach the arms forward, forehead down, for about a minute. Widen the knees if the hips need room."],
  [35, "Knees-to-chest rock", "Lower back & core", "S", "30 s", "Lie on your back, hug both knees in, and rock gently side to side for about 30 seconds. Keep the head down and the breath easy."],
  [36, "Dead bug", "Lower back & core", "D", "2x8 per side", "Lie on your back with the arms and knees up, then reach the opposite arm and leg away for two sets of eight each side. Press the low back gently toward the floor."],
  [37, "Open book rotation", "Upper back", "D", "8 per side", "Lie on one side with the knees bent and open the top arm across until it reaches toward the floor behind you, for eight each side. Let the chest follow the arm and keep the knees stacked."],
  [38, "Thread the needle", "Upper back", "S", "30 s per side", "From hands and knees, slide one arm under the chest and rest that shoulder and the side of the head down for 30 seconds each side. The other hand stays planted so you can come out."],
  [39, "World's greatest stretch", "Upper back", "D", "5 per side", "Step into a deep lunge, set the same-side hand on the floor, and reach the other arm toward the ceiling for five each side. Keep the front heel down and the back leg long."],
  [40, "Doorway chest stretch", "Shoulders, chest & neck", "S", "30 s", "Stand in a doorway with the forearms on the frame and step through until the chest opens, for about 30 seconds. Keep the ribs down so the stretch stays in the chest."],
  [41, "Arm circles", "Shoulders, chest & neck", "D", "10 each direction", "Stand and circle the arms forward ten times, then back ten times. Keep the shoulders away from the ears and let the circles grow from small to easy."],
  [42, "Neck side stretch", "Shoulders, chest & neck", "S", "20-30 s per side", "Sit or stand tall and tilt one ear toward that shoulder for 20 to 30 seconds each side. Keep the opposite shoulder heavy and do not pull on the head."],
];

export const EXERCISES: readonly Exercise[] = ROWS.map(([id, name, area, type, dose, howTo]) => ({
  id,
  name,
  area,
  type,
  dose,
  howTo,
}));

export const EXERCISE_AREAS: readonly string[] = [...new Set(EXERCISES.map((exercise) => exercise.area))];

const byId = new Map(EXERCISES.map((exercise) => [exercise.id, exercise]));

export function exerciseById(id: number): Exercise | undefined {
  return byId.get(id);
}

export const ROUTINES: readonly Routine[] = [
  { id: "pre-run", name: "Pre-run warm-up", minutes: 8, exerciseIds: [1, 12, 26, 17, 21, 39] },
  { id: "post-run", name: "Post-run cooldown", minutes: 10, exerciseIds: [5, 6, 14, 16, 19, 22] },
  { id: "long-recovery", name: "Saturday long-run recovery", minutes: 12, exerciseIds: [3, 6, 20, 23, 28, 34, 31] },
  { id: "yoga", name: "Recovery-day yoga flow", minutes: 12, exerciseIds: [33, 8, 19, 23, 37, 38, 34] },
  { id: "hips", name: "Hips & glutes mobility", minutes: 10, exerciseIds: [24, 25, 32, 22, 27, 29] },
  { id: "primer", name: "Pre-race primer", minutes: 6, exerciseIds: [1, 12, 26, 13, 21, 41] },
];

const routineMap = new Map(ROUTINES.map((routine) => [routine.id, routine]));

export function routineById(id: string): Routine | undefined {
  return routineMap.get(id);
}

export const REGIONS: readonly Region[] = [
  { id: "feet", label: "Feet & ankles", extraIds: [3, 4, 1], color: "#3d8bfd" },
  { id: "calves", label: "Calves / Achilles", extraIds: [5, 6, 8], color: "#7a5af8" },
  { id: "shins", label: "Shins", extraIds: [9, 10, 11], color: "#2bb0a0" },
  { id: "hamstrings", label: "Hamstrings", extraIds: [14, 15, 13], color: "#e15b73" },
  { id: "quads", label: "Quads", extraIds: [16, 18, 17], color: "#ef8b3a" },
  { id: "hip-flexors", label: "Hip flexors", extraIds: [19, 20, 21], color: "#e2b43a" },
  { id: "glutes", label: "Glutes / piriformis", extraIds: [22, 23, 24], color: "#3d5fd6" },
  { id: "adductors", label: "Adductors", extraIds: [27, 28, 29], color: "#5b9bd6" },
  { id: "it-band", label: "IT band / outer hip", extraIds: [30, 31, 32], color: "#3dae6a" },
  { id: "lower-back", label: "Lower back", extraIds: [34, 35, 33], color: "#e6c24a" },
  { id: "abs", label: "Abs / core", extraIds: [33, 35, 36], color: "#8b6fd4" },
  { id: "upper-back", label: "Upper back", extraIds: [37, 38, 39], color: "#e15b64" },
  { id: "shoulders", label: "Shoulders / chest", extraIds: [40, 41], color: "#e07a45" },
  { id: "neck", label: "Neck", extraIds: [42], color: "#f0a05a" },
];

const regionMap = new Map(REGIONS.map((region) => [region.id, region]));

export function regionById(id: string): Region | undefined {
  return regionMap.get(id);
}

export const SHARP_MESSAGE =
  "Stop stretching that area. Rest it, and see a physio or doctor. Sharp pain, or pain that is getting worse, is not a reason to stretch.";

export const STRETCH_DISCLAIMER =
  "These stretches are general guidance for runners, not medical care. If pain is sharp, swollen, or getting worse, stop and see a physio or doctor.";

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] as const;
const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

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

function weekdayOf(iso: string): string {
  const match = ISO.exec(iso);
  if (!match) return "";
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return "";
  return WEEKDAYS[date.getUTCDay()];
}

export type DayKind = "quality" | "long" | "easy" | "rest" | "race";

export type StretchSession = {
  date?: string;
  day_of_week?: string;
  template_id?: string;
  reason_codes?: string[];
};

export type Severity = "mild" | "moderate" | "sharp";

export type SoreSpot = {
  region: string;
  severity: Severity;
  started_on: string;
  check_in_on: string;
  cleared: boolean;
};

export type Completion = {
  date: string;
  routine_id: string;
};

export type PrescribedRoutine = {
  routine: Routine;
  exercises: Exercise[];
  done: boolean;
};

export type Prescription = {
  today: string;
  kind: DayKind;
  kindLabel: string;
  extras: Exercise[];
  routines: PrescribedRoutine[];
  sharp: Region[];
  checkIns: Region[];
};

/** Saturday long-run ladder from the season engine, 9.5 km through 15 km. */
const LONG_LADDER = new Set(
  [9500, 10000, 10500, 11000, 11500, 12000, 12500, 13000, 13500, 14000, 14500, 15000].map(
    (meters) => `aer_${meters}_r0_x1`,
  ),
);

const RACE_ID = "rr_800_r0_x1";

const KIND_LABEL: Record<DayKind, string> = {
  quality: "Hard day",
  long: "Long run",
  easy: "Easy day",
  rest: "Rest day",
  race: "Race day",
};

const KIND_ROUTINES: Record<Exclude<DayKind, "easy">, readonly string[]> = {
  quality: ["pre-run", "post-run"],
  long: ["pre-run", "long-recovery"],
  rest: ["yoga"],
  race: ["primer"],
};

export function easyRoutineId(iso: string): "hips" | "yoga" {
  const index = WEEKDAYS.indexOf(weekdayOf(iso) as (typeof WEEKDAYS)[number]);
  if (index < 0) return "yoga";
  return index % 2 === 0 ? "hips" : "yoga";
}

export function classifyDay(today: string, session: StretchSession | null | undefined): DayKind {
  if (!session) return "rest";
  if (session.date && session.date !== today) return "rest";
  const template = (session.template_id || "").trim();
  if (!template) return "rest";
  if (template === RACE_ID) return "race";
  const dow = (session.day_of_week || "").trim() || weekdayOf(today);
  const codes = session.reason_codes || [];
  const longCoded = codes.includes("weekly_aerobic_long_run") || LONG_LADDER.has(template);
  if (dow === "Saturday" && longCoded) return "long";
  const easy = template.startsWith("aer_") || codes.includes("extra_easy_day");
  if (easy) return "easy";
  if (dow === "Tuesday" || dow === "Thursday") return "quality";
  return "quality";
}

export function routineIdsFor(today: string, kind: DayKind): string[] {
  if (kind === "easy") return [easyRoutineId(today)];
  return [...KIND_ROUTINES[kind]];
}

export function spotState(spot: SoreSpot, today: string): "cleared" | "sharp" | "active" | "check-in" {
  if (spot.cleared) return "cleared";
  if (spot.severity === "sharp") return "sharp";
  if (today < spot.check_in_on) return "active";
  return "check-in";
}

export function extraExercises(spots: readonly SoreSpot[], today: string): Exercise[] {
  const seen = new Set<number>();
  const found: Exercise[] = [];
  for (const spot of spots) {
    if (spotState(spot, today) !== "active") continue;
    const region = regionById(spot.region);
    if (!region) continue;
    for (const id of region.extraIds) {
      if (seen.has(id)) continue;
      const exercise = exerciseById(id);
      if (!exercise) continue;
      seen.add(id);
      found.push(exercise);
    }
  }
  return found;
}

export function prescribe(input: {
  today: string;
  session: StretchSession | null | undefined;
  spots?: readonly SoreSpot[];
  completions?: readonly Completion[];
}): Prescription {
  const spots = input.spots ?? [];
  const completions = input.completions ?? [];
  const kind = classifyDay(input.today, input.session);
  const done = new Set(
    completions.filter((row) => row.date === input.today).map((row) => row.routine_id),
  );
  const routines: PrescribedRoutine[] = [];
  for (const id of routineIdsFor(input.today, kind)) {
    const routine = routineById(id);
    if (!routine) continue;
    const exercises = routine.exerciseIds
      .map((exerciseId) => exerciseById(exerciseId))
      .filter((exercise): exercise is Exercise => Boolean(exercise));
    routines.push({ routine, exercises, done: done.has(routine.id) });
  }
  const sharp: Region[] = [];
  const checkIns: Region[] = [];
  for (const spot of spots) {
    const region = regionById(spot.region);
    if (!region) continue;
    const state = spotState(spot, input.today);
    if (state === "sharp") sharp.push(region);
    if (state === "check-in") checkIns.push(region);
  }
  return {
    today: input.today,
    kind,
    kindLabel: KIND_LABEL[kind],
    extras: extraExercises(spots, input.today),
    routines,
    sharp,
    checkIns,
  };
}

export function weekStart(iso: string): string {
  const index = WEEKDAYS.indexOf(weekdayOf(iso) as (typeof WEEKDAYS)[number]);
  if (index < 0) return iso;
  return shiftDays(iso, -index);
}

export function weekProgress(completions: readonly Completion[], today: string): {
  routines: number;
  days: number;
  streak: number;
} {
  const start = weekStart(today);
  const end = shiftDays(start, 6);
  const inWeek = completions.filter((row) => row.date >= start && row.date <= end);
  const days = new Set(inWeek.map((row) => row.date)).size;
  const have = new Set(completions.map((row) => row.date));
  let cursor = have.has(today) ? today : shiftDays(today, -1);
  let streak = 0;
  while (have.has(cursor) && streak < 400) {
    streak += 1;
    cursor = shiftDays(cursor, -1);
  }
  return { routines: inWeek.length, days, streak };
}

export function weekLabel(progress: { routines: number; streak: number }): string {
  const routines =
    progress.routines === 1 ? "1 routine done this week" : `${progress.routines} routines done this week`;
  const streak =
    progress.streak === 1 ? "1-day streak" : progress.streak > 1 ? `${progress.streak}-day streak` : "No streak yet";
  return `${routines} · ${streak}`;
}

export function filterExercises(area: string, type: StretchType | "All"): Exercise[] {
  return EXERCISES.filter((exercise) => {
    if (area && area !== "All" && exercise.area !== area) return false;
    if (type !== "All" && exercise.type !== type) return false;
    return true;
  });
}

export function exercisesOf(routine: Routine): Exercise[] {
  return routine.exerciseIds
    .map((id) => exerciseById(id))
    .filter((exercise): exercise is Exercise => Boolean(exercise));
}

