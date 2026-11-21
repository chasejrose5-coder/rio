import assert from "node:assert/strict";
import test from "node:test";
import { CREATORS } from "./creators-copy.ts";

function visibleCreatorLines(): string[] {
  return [CREATORS.banner, CREATORS.heading, CREATORS.alt, CREATORS.name, ...CREATORS.paragraphs, CREATORS.close];
}

test("Creators describes any runner's season", () => {
  const visible = visibleCreatorLines().join("\n");
  assert.equal(CREATORS.heading, "Built for any runner.");
  assert.equal(CREATORS.banner, "Creators");
  assert.equal(CREATORS.alt, "Aerial view of an empty track.");
  assert.equal(CREATORS.name, "Your season");
  assert.equal(CREATORS.paragraphs.length, 3);
  assert.match(visible, /the 800 you can run now/);
  assert.match(visible, /Strava can bring the runs in/);
  assert.match(visible, /Every rep has a reason\./);
  for (const banned of ["Chase", "Jay", "Bentley", "Stanford", "1:55", "chasejrose", "Editable placeholder"]) {
    assert.equal(visible.includes(banned), false, banned);
  }
});
