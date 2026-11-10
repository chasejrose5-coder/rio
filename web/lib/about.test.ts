import assert from "node:assert/strict";
import test from "node:test";
import { ABOUT } from "./about-copy.ts";

function visibleAboutLines(): string[] {
  const lines: string[] = [ABOUT.heading, ABOUT.credit];
  for (const section of ABOUT.sections) {
    lines.push(section.title, ...section.visible);
    for (const row of section.rows) lines.push(row.label, row.line);
    lines.push(...section.closing);
  }
  return lines;
}

function hiddenAboutLines(): string[] {
  return ABOUT.sections.flatMap((section) => [...section.hidden]);
}

test("the visible About lines keep the short copy and leave $25 hidden", () => {
  const visible = visibleAboutLines().join("\n");
  const hidden = hiddenAboutLines().join("\n");
  assert.match(visible, /Friday is off/);
  assert.match(visible, /The short fast reps step up from phase 1/);
  assert.match(visible, /The reps are longer than in phase 4/);
  assert.match(visible, /The taper stays fresh\. No hard speed endurance or anaerobic work\./);
  assert.match(visible, /Photo by Botond Dobozi on Pexels/);
  assert.equal(visible.includes("$25"), false);
  assert.equal(visible.includes("on_track"), false);
  assert.match(hidden, /Those calls stop once recorded spend reaches \$25\./);
  assert.match(hidden, /on_track/);
  assert.match(hidden, /Classification is rules, not AI\./);
  assert.equal(visible.includes("probability"), false);
  assert.equal(visible.includes("readiness_score"), false);
});
