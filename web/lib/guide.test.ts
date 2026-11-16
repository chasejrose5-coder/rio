import assert from "node:assert/strict";
import test from "node:test";
import { GUIDE_SECTIONS, GUIDE_TITLE, PAGE_MEANINGS, meaningHref } from "./guide-copy.ts";

const BANNED = ["probability", "readiness_score", "Chase", "Jay Rose", "Jay"];

function sentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

test("every page note is two to four sentences and links to a real section", () => {
  const ids = new Set(GUIDE_SECTIONS.map((section) => section.id));
  for (const [page, meaning] of Object.entries(PAGE_MEANINGS)) {
    const count = meaning.sentences.flatMap((line) => sentences(line)).length;
    assert.ok(count >= 2 && count <= 4, `${page} has ${count} sentences`);
    assert.ok(ids.has(meaning.section), `${page} links to a missing section`);
    assert.equal(meaningHref(meaning.section), `/guide#${meaning.section}`);
    const joined = meaning.sentences.join(" ");
    for (const word of BANNED) {
      assert.equal(joined.includes(word), false, `${page} includes ${word}`);
    }
  }
});

test("the guide states the week, the paces, and the lines from the season rules", () => {
  const text = [GUIDE_TITLE, ...GUIDE_SECTIONS.flatMap((section) => [section.title, ...section.paragraphs])].join("\n");
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
  for (const word of BANNED) assert.equal(text.includes(word), false, word);
  assert.equal(text.includes("<img"), false);
});

test("page sections use the same sentences as the footer notes", () => {
  for (const [page, meaning] of Object.entries(PAGE_MEANINGS)) {
    if (page === "guide") continue;
    const section = GUIDE_SECTIONS.find((item) => item.id === meaning.section);
    assert.ok(section, page);
    assert.deepEqual(section.paragraphs, meaning.sentences);
  }
});
