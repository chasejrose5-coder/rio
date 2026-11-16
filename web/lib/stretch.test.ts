import assert from "node:assert/strict";
import test from "node:test";
import { existsSync, readFileSync } from "node:fs";
import { backMuscles, backOutline, frontMuscles, frontOutline } from "../components/body-map/paths.ts";
import { BACK_EXTRAS, FRONT_EXTRAS, REGION_OF } from "./body-regions.ts";
import { expandDrawn, midlineOf, mirrorPath, samePath } from "./body-symmetry.ts";
import { EXERCISES, REGIONS, ROUTINES, SHARP_MESSAGE, type DayKind } from "./stretch-content.ts";
import {
  classifyDay,
  extraExercises,
  filterExercises,
  occurrenceBefore,
  prescribe,
  routinesFor,
  spotState,
  weekLabel,
  weekProgress,
  type SoreSpot,
  type StretchSession,
} from "./stretch-content.ts";

const BANNED = ["probability", "readiness_score", "Chase", "Jay Rose", "Jay"];

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function spot(partial: Partial<SoreSpot> & Pick<SoreSpot, "region" | "severity">): SoreSpot {
  return {
    started_on: "2026-11-10",
    check_in_on: "2026-11-17",
    cleared: false,
    ...partial,
  };
}

test("the library is the 42 named stretches, as text only", () => {
  assert.equal(EXERCISES.length, 42);
  assert.deepEqual(
    EXERCISES.map((exercise) => exercise.id),
    Array.from({ length: 42 }, (_, index) => index + 1),
  );
  assert.equal(new Set(EXERCISES.map((exercise) => exercise.name)).size, 42);
  assert.equal(existsSync(new URL("./stretch-poses.ts", import.meta.url).pathname), false);
  const view = readFileSync(new URL("../components/StretchView.tsx", import.meta.url), "utf8");
  const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");
  assert.equal(view.includes("ExerciseArt"), false);
  assert.equal(view.includes("<svg"), false);
  assert.equal(view.includes("rio-stretch-art"), false);
  assert.equal(css.includes("rio-stretch-art"), false);
  assert.equal(css.includes(".rio-stretch-card {\n  display: grid;"), false);
  for (const exercise of EXERCISES) {
    const count = sentences(exercise.howTo).length;
    assert.ok(count >= 2 && count <= 3, `${exercise.id} has ${count} sentences`);
    assert.ok(exercise.dose.length > 0);
    assert.ok(exercise.type === "D" || exercise.type === "S");
    for (const word of BANNED) assert.equal(exercise.howTo.includes(word), false, word);
  }
  const slugs = new Set([...frontMuscles, ...backMuscles].map((muscle) => muscle.slug));
  for (const slug of ["chest", "abs", "quadriceps", "tibialis", "calves", "feet", "ankles", "hamstring", "gluteal", "adductors", "lower-back", "upper-back", "trapezius", "deltoids", "neck"]) {
    assert.equal(slugs.has(slug), true, slug);
  }
  const license = readFileSync(new URL("../components/body-map/LICENSE", import.meta.url), "utf8");
  assert.match(license, /MIT License/);
  assert.match(license, /Copyright \(c\) 2022 ELABBASSI Hicham/);
  const map = readFileSync(new URL("../components/BodyMap.tsx", import.meta.url), "utf8");
  assert.match(map, /Body outlines: react-native-body-highlighter \(MIT\) by HichamELBSI/);
  assert.match(map, /hip-flexors/);
  assert.match(map, /it-band/);
  assert.equal(EXERCISES[0].dose, "10 each way per foot");
  assert.equal(EXERCISES[41].name, "Neck side stretch");
  assert.equal(EXERCISES[41].type, "S");
});

test("every body region has a matching path on the left and the right", () => {
  const views = [
    { muscles: frontMuscles, outline: frontOutline, extras: FRONT_EXTRAS },
    { muscles: backMuscles, outline: backOutline, extras: BACK_EXTRAS },
  ];
  for (const view of views) {
    const mid = midlineOf(view.outline);
    const byRegion = new Map<string, Map<string, string[]>>();
    for (const muscle of view.muscles) {
      const region = REGION_OF[muscle.slug];
      if (!region) continue;
      const slugs = byRegion.get(region) ?? new Map<string, string[]>();
      slugs.set(muscle.slug, [...muscle.paths]);
      byRegion.set(region, slugs);
    }
    for (const extra of view.extras) {
      const slugs = byRegion.get(extra.region) ?? new Map<string, string[]>();
      slugs.set(extra.region, [...(slugs.get(extra.region) ?? []), ...extra.paths]);
      byRegion.set(extra.region, slugs);
    }
    assert.ok(byRegion.size >= 8);
    for (const [region, slugs] of byRegion) {
      for (const [slug, paths] of slugs) {
        const drawn = expandDrawn(paths, mid);
        const left = drawn.filter((part) => part.place === "left");
        const right = drawn.filter((part) => part.place === "right");
        assert.equal(left.length, right.length, `${region} ${slug} count`);
        assert.ok(left.length + drawn.some((part) => part.place === "cross"), `${region} ${slug} has a side`);
        for (const part of left) {
          const mirror = mirrorPath(part.d, mid);
          assert.ok(
            right.some((other) => samePath(other.d, mirror)),
            `${region} ${slug} mirror`,
          );
        }
        for (const part of drawn) {
          const mirror = mirrorPath(part.d, mid);
          assert.ok(
            drawn.some((other) => samePath(other.d, mirror)),
            `${region} ${slug} pair`,
          );
        }
      }
    }
  }
});

test("each day type has its own warm-ups and cooldowns", () => {
  const kinds: DayKind[] = ["quality", "long", "easy", "rest", "race"];
  const ids = ROUTINES.map((routine) => routine.id);
  assert.equal(new Set(ids).size, ids.length);
  const lists = ROUTINES.map((routine) => routine.exerciseIds.join(","));
  assert.equal(new Set(lists).size, lists.length);
  for (const routine of ROUTINES) {
    for (const exerciseId of routine.exerciseIds) {
      assert.ok(EXERCISES.some((exercise) => exercise.id === exerciseId), `${routine.id} ${exerciseId}`);
    }
  }
  for (const kind of kinds) {
    assert.ok(routinesFor(kind, "warm-up").length >= 3, kind);
    assert.ok(routinesFor(kind, "cooldown").length >= 3, kind);
    const owned = new Set(ROUTINES.filter((routine) => routine.kind === kind).map((routine) => routine.id));
    for (const other of kinds) {
      if (other === kind) continue;
      for (const routine of routinesFor(other, "warm-up").concat(routinesFor(other, "cooldown"))) {
        assert.equal(owned.has(routine.id), false, `${routine.id} is shared`);
      }
    }
  }
  for (const routine of routinesFor("quality", "warm-up")) {
    const dynamic = routine.exerciseIds.filter((id) => EXERCISES.find((exercise) => exercise.id === id)?.type === "D");
    assert.ok(dynamic.length >= 4, routine.id);
  }
  for (const routine of routinesFor("long", "cooldown")) {
    const idsIn = new Set(routine.exerciseIds);
    assert.ok([3, 4, 5, 6].some((id) => idsIn.has(id)), routine.id);
    assert.ok([19, 20, 22, 23, 27, 28].some((id) => idsIn.has(id)), routine.id);
    assert.ok(routine.exerciseIds.length >= 7, routine.id);
  }
  for (const routine of ROUTINES.filter((item) => item.kind === "easy" || item.kind === "race")) {
    assert.ok(routine.exerciseIds.length <= 6, routine.id);
  }
  const original = Object.fromEntries(ROUTINES.map((routine) => [routine.id, routine.exerciseIds]));
  assert.deepEqual(original["pre-run"], [1, 12, 26, 17, 21, 39]);
  assert.deepEqual(original["post-run"], [5, 6, 14, 16, 19, 22]);
  assert.deepEqual(original["long-recovery"], [3, 6, 20, 23, 28, 34, 31]);
  assert.deepEqual(original.yoga, [33, 8, 19, 23, 37, 38, 34]);
  assert.deepEqual(original.hips, [24, 25, 32, 22, 27, 29]);
  assert.deepEqual(original.primer, [1, 12, 26, 13, 21, 41]);
});

function day(date: string, template: string, dow: string, codes: string[] = []): StretchSession {
  return { date, day_of_week: dow, template_id: template, reason_codes: codes };
}

test("each plan day type picks from its own pool, and the date rotates it", () => {
  const week: StretchSession[] = [
    day("2026-11-08", "aer_5000_r0_x1", "Sunday"),
    day("2026-11-09", "aer_5000_r0_x1", "Monday"),
    day("2026-11-10", "se_400_r90_x6", "Tuesday", ["phase_4"]),
    day("2026-11-11", "aer_5000_r0_x1", "Wednesday"),
    day("2026-11-12", "ap_600_r75_x6", "Thursday"),
    day("2026-11-14", "aer_12000_r0_x1", "Saturday", ["weekly_aerobic_long_run"]),
  ];
  const on = (date: string) => {
    const session = week.find((item) => item.date === date) ?? null;
    return prescribe({ today: date, session, sessions: week });
  };

  const tuesday = on("2026-11-10");
  const thursday = on("2026-11-12");
  assert.equal(tuesday.kind, "quality");
  assert.equal(thursday.kind, "quality");
  assert.equal(tuesday.routines.length, 2);
  assert.notEqual(tuesday.routines[0]?.routine.id, thursday.routines[0]?.routine.id);
  assert.notEqual(tuesday.routines[1]?.routine.id, thursday.routines[1]?.routine.id);
  for (const item of tuesday.routines) assert.equal(item.routine.kind, "quality");
  assert.deepEqual(on("2026-11-10"), tuesday);

  const sunday = on("2026-11-08");
  const monday = on("2026-11-09");
  const wednesday = on("2026-11-11");
  assert.equal(sunday.kind, "easy");
  assert.equal(monday.kind, "easy");
  assert.equal(wednesday.kind, "easy");
  assert.notEqual(sunday.routines[0]?.routine.id, monday.routines[0]?.routine.id);
  assert.notEqual(monday.routines[0]?.routine.id, wednesday.routines[0]?.routine.id);
  assert.notEqual(sunday.routines[1]?.routine.id, monday.routines[1]?.routine.id);
  for (const item of sunday.routines) assert.equal(item.routine.kind, "easy");

  const friday = prescribe({ today: "2026-11-13", session: null, sessions: week });
  assert.equal(friday.kind, "rest");
  for (const item of friday.routines) assert.equal(item.routine.kind, "rest");

  const long = on("2026-11-14");
  assert.equal(long.kind, "long");
  for (const item of long.routines) assert.equal(item.routine.kind, "long");
  assert.ok(long.routines.some((item) => item.routine.slot === "cooldown" && item.routine.minutes >= 12));

  const raceWeek = week.map((item) =>
    item.date === "2026-11-14" ? day("2026-11-14", "rr_800_r0_x1", "Saturday") : item,
  );
  const race = prescribe({
    today: "2026-11-14",
    session: raceWeek.find((item) => item.date === "2026-11-14"),
    sessions: raceWeek,
  });
  assert.equal(race.kind, "race");
  for (const item of race.routines) assert.equal(item.routine.kind, "race");

  const nextTuesday = day("2026-11-17", "se_400_r90_x6", "Tuesday");
  const next = prescribe({ today: "2026-11-17", session: nextTuesday, sessions: [nextTuesday] });
  assert.notEqual(next.routines[0]?.routine.id, tuesday.routines[0]?.routine.id);
  assert.equal(occurrenceBefore("2026-11-12", "quality", week), 1);
  assert.equal(occurrenceBefore("2026-11-10", "quality", week), 0);

  const thursdayKind = classifyDay("2026-11-12", {
    date: "2026-11-12",
    day_of_week: "Thursday",
    template_id: "ap_600_r75_x6",
  });
  assert.equal(thursdayKind, "quality");

  const easyTuesday = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "aer_5000_r0_x1", reason_codes: ["extra_easy_day"] },
  });
  assert.equal(easyTuesday.kind, "easy");
  for (const item of easyTuesday.routines) assert.equal(item.routine.kind, "easy");

  const wednesdayHold = prescribe({
    today: "2026-11-11",
    session: {
      date: "2026-11-11",
      day_of_week: "Wednesday",
      template_id: "aer_10000_r0_x1",
      reason_codes: ["weekly_aerobic_long_run", "extra_easy_day"],
    },
  });
  assert.equal(wednesdayHold.kind, "easy");

  const emptyTuesday = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "" },
  });
  assert.equal(emptyTuesday.kind, "rest");

  const wrongDay = prescribe({
    today: "2026-11-13",
    session: { date: "2026-11-14", day_of_week: "Saturday", template_id: "aer_12000_r0_x1" },
  });
  assert.equal(wrongDay.kind, "rest");
});

test("mild and moderate spots add extras for 7 days, then ask, and sharp adds nothing", () => {
  const calves = spot({ region: "calves", severity: "moderate" });
  const onStart = extraExercises([calves], "2026-11-10").map((exercise) => exercise.id);
  assert.deepEqual(onStart, [5, 6, 8]);
  assert.equal(spotState(calves, "2026-11-16"), "active");
  assert.deepEqual(extraExercises([calves], "2026-11-16").map((exercise) => exercise.id), [5, 6, 8]);
  assert.equal(spotState(calves, "2026-11-17"), "check-in");
  assert.deepEqual(extraExercises([calves], "2026-11-17"), []);

  const prescribed = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
    spots: [calves, spot({ region: "hamstrings", severity: "mild" })],
  });
  assert.deepEqual(prescribed.extras.map((exercise) => exercise.id), [5, 6, 8, 14, 15, 13]);
  assert.equal(prescribed.routines.length, 2);
  assert.ok(prescribed.routines.every((item) => item.routine.kind === "quality"));
  assert.equal(prescribed.sharp.length, 0);

  const sharp = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
    spots: [spot({ region: "calves", severity: "sharp" })],
  });
  assert.deepEqual(sharp.extras, []);
  assert.equal(sharp.sharp[0]?.label, "Calves / Achilles");
  assert.match(SHARP_MESSAGE, /Stop stretching that area/);

  const cleared = prescribe({
    today: "2026-11-10",
    session: null,
    spots: [spot({ region: "neck", severity: "mild", cleared: true })],
  });
  assert.deepEqual(cleared.extras, []);
  assert.deepEqual(cleared.checkIns, []);

  const neck = extraExercises([spot({ region: "neck", severity: "mild" })], "2026-11-10");
  assert.deepEqual(neck.map((exercise) => exercise.id), [42]);
  const abs = REGIONS.find((region) => region.id === "abs");
  assert.deepEqual(abs?.extraIds, [33, 35, 36]);
});

test("done marks count for this week and the streak stops at a gap", () => {
  const progress = weekProgress(
    [
      { date: "2026-11-09", routine_id: "yoga" },
      { date: "2026-11-10", routine_id: "pre-run" },
      { date: "2026-11-10", routine_id: "post-run" },
      { date: "2026-11-08", routine_id: "hips" },
    ],
    "2026-11-10",
  );
  assert.equal(progress.routines, 4);
  assert.equal(progress.days, 3);
  assert.equal(progress.streak, 3);
  assert.equal(weekLabel(progress), "4 routines done this week · 3-day streak");

  const gap = weekProgress([{ date: "2026-11-08", routine_id: "yoga" }], "2026-11-10");
  assert.equal(gap.streak, 0);
  assert.match(weekLabel(gap), /No streak yet/);

  const open = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
  });
  const marked = prescribe({
    today: "2026-11-10",
    session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: "se_400_r90_x6" },
    completions: [{ date: "2026-11-10", routine_id: open.routines[0]?.routine.id || "" }],
  });
  assert.equal(marked.routines[0]?.done, true);
  assert.equal(marked.routines[1]?.done, false);
});

test("the library filters by area and by dynamic or static", () => {
  assert.equal(filterExercises("All", "All").length, 42);
  assert.equal(filterExercises("Hamstrings", "All").length, 4);
  assert.deepEqual(
    filterExercises("Hamstrings", "S").map((exercise) => exercise.id),
    [14, 15],
  );
  assert.equal(filterExercises("Shins", "D").length, 2);
});
