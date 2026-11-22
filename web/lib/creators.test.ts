import assert from "node:assert/strict";
import test from "node:test";
import { CREATORS } from "./creators-copy.ts";

function visibleCreatorLines(): string[] {
  return [CREATORS.banner, CREATORS.heading, CREATORS.alt, CREATORS.name, ...CREATORS.paragraphs, CREATORS.close];
}

test("Creators shows Chase's three paragraphs and keeps Jay in the comment", () => {
  const visible = visibleCreatorLines().join("\n");
  assert.equal(CREATORS.heading, "Built by a runner, for runners.");
  assert.equal(CREATORS.banner, "Creators");
  assert.equal(CREATORS.alt, "Chase Rose exploding out of the starting blocks.");
  assert.equal(CREATORS.name, "Chase Rose, Founder");
  assert.equal(CREATORS.paragraphs.length, 3);
  assert.match(visible, /Bentley Upper School/);
  assert.match(visible, /patellar tendon injury/);
  assert.match(visible, /The plan adjusts to what you actually run instead of pushing you past it\./);
  assert.match(visible, /Every rep has a reason\./);
  assert.equal(visible.includes("Jay Rose"), false);
  assert.equal(visible.includes("Editable placeholder"), false);
  assert.equal(visible.includes("Photo by"), false);
  assert.match(CREATORS.comment, /Jay Rose/);
  assert.match(CREATORS.comment, /Editable placeholder text\. A short bio for Jay Rose goes here\./);
  assert.match(CREATORS.comment, /Bio coming soon\./);
  assert.equal(CREATORS.comment.startsWith("<!--"), true);
  assert.equal(CREATORS.comment.endsWith("-->"), true);
});
