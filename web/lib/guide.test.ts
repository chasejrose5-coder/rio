import assert from "node:assert/strict";
import test from "node:test";
import { GUIDE_SECTIONS, GUIDE_TITLE, PAGE_MEANINGS, guidePlainText, meaningHref } from "./guide-copy.ts";

const BANNED = ["probability", "readiness_score", "Chase", "Jay Rose", "Jay"];

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

test("every page note is one or two sentences and links to a real section", () => {
  const ids = new Set(GUIDE_SECTIONS.map((section) => section.id));
  for (const [page, meaning] of Object.entries(PAGE_MEANINGS)) {
    const count = meaning.sentences.flatMap((line) => sentences(line)).length;
    assert.ok(count >= 1 && count <= 2, `${page} has ${count} sentences`);
    assert.ok(ids.has(meaning.section), `${page} links to a missing section`);
    assert.equal(meaningHref(meaning.section), `/guide#${meaning.section}`);
    const joined = meaning.sentences.join(" ");
    for (const word of BANNED) {
      assert.equal(joined.includes(word), false, `${page} includes ${word}`);
    }
  }
});

test("the guide states the week, the paces, and the lines from the season rules", () => {
  const text = guidePlainText();
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  // The guide before the About rules moved here was capped at 1,100 words.
  // Those sections are included as written, so the cap moved with them.
  assert.ok(words <= 1800, `guide is ${words} words`);
  assert.ok(words >= 700, `guide is ${words} words`);
  assert.match(text, /9\.5 km/);
  assert.match(text, /500 m/);
  assert.match(text, /15 km/);
  assert.match(text, /at most 10%/);
  assert.match(text, /Tuesday and Thursday/);
  assert.match(text, /Saturday is the long run/);
  assert.match(text, /7:25/);
  assert.match(text, /Easy and long runs use/);
  assert.match(text, /Quality workouts stay on your 800|quality workouts stay on your 800/);
  assert.match(text, /their average/);
  assert.match(text, /No runs yet/);
  assert.match(text, /On track/);
  assert.match(text, /Not hitting/);
  assert.match(text, /Smashing/);
  assert.match(text, /Strava is the only place runs are imported from/);
  assert.match(text, /Workouts logged|workouts logged/);
  assert.match(text, /Classification is rules, not AI/);
  assert.match(text, /times 10/);
  assert.match(text, /times 11/);
  assert.match(text, /The short fast reps step up from phase 1/);
  assert.match(text, /A training block is one phase of the season/);
  assert.match(text, /A timed effort is a run you logged/);
  assert.match(text, /Times use minutes:seconds\.tenths, like 2:05\.0/);
  assert.match(text, /on_track/);
  assert.match(text, /Those calls stop once recorded spend reaches \$25/);
  for (const word of BANNED) assert.equal(text.includes(word), false, word);
  assert.equal(text.includes("<img"), false);
});

test("the guide opens with the everyday sections", () => {
  assert.deepEqual(
    GUIDE_SECTIONS.slice(0, 4).map((section) => section.id),
    ["getting-started", "today", "paces", "week"],
  );
  assert.ok(GUIDE_SECTIONS.some((section) => section.details?.some((detail) => detail.summary === "The eight phases")));
  assert.ok(GUIDE_SECTIONS.some((section) => section.details?.some((detail) => detail.summary === "Long-run ladder")));
  assert.deepEqual(
    GUIDE_SECTIONS.map((section) => section.id).filter((id) =>
      ["ten-percent", "classification", "hard-days"].includes(id),
    ),
    ["ten-percent", "classification", "hard-days"],
  );
});

test("admin and internal pages stay off the guide", () => {
  const titles = GUIDE_SECTIONS.map((section) => section.title);
  const ids = GUIDE_SECTIONS.map((section) => section.id);
  for (const title of ["Admin", "Creators", "Next", "Decisions", "Ledger", "Last Session", "Goal"]) {
    assert.equal(titles.includes(title), false, title);
  }
  for (const id of ["admin", "creators", "next", "decisions", "ledger", "last-session", "goal"]) {
    assert.equal(ids.includes(id), false, id);
  }
  const classification = GUIDE_SECTIONS.find((section) => section.id === "classification");
  const kept = classification
    ? [
        classification.title,
        ...classification.paragraphs,
        ...(classification.details ?? []).flatMap((detail) => [detail.summary, ...detail.paragraphs]),
      ].join("\n")
    : "";
  const text = guidePlainText().replace(kept, "");
  assert.equal(text.includes("Creators"), false);
  assert.equal(text.includes("Last Session"), false);
  assert.equal(text.includes("Decisions"), false);
  assert.equal(text.includes("Ledger"), false);
  assert.equal(/\bAdmin\b/.test(text), false);
});
