import assert from "node:assert/strict";
import test from "node:test";
import { ABOUT } from "./about-copy.ts";
import { guidePlainText } from "./guide-copy.ts";

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

test("the visible About lines are the short intro and the rules live in the guide", () => {
  const visible = visibleAboutLines().join("\n");
  const hidden = hiddenAboutLines().join("\n");
  assert.match(visible, /RIO plans an 800 m season from rules/);
  assert.match(visible, /You enter the 800 you can run now/);
  assert.match(visible, /The full details are in the Guide after you sign in/);
  assert.match(visible, /Photo by Botond Dobozi on Pexels/);
  assert.equal(visible.includes("$25"), false);
  assert.equal(hidden.includes("$25"), false);
  assert.equal(visible.includes("on_track"), false);
  assert.equal(visible.includes("probability"), false);
  assert.equal(visible.includes("readiness_score"), false);
  const guide = guidePlainText();
  assert.match(guide, /The short fast reps step up from phase 1/);
  assert.match(guide, /The reps are longer than in phase 4/);
  assert.match(guide, /The taper stays fresh\. No hard speed endurance or anaerobic work\./);
  assert.match(guide, /Classification is rules, not AI\./);
  assert.match(guide, /Those calls stop once recorded spend reaches \$25\./);
  assert.match(guide, /on_track/);
});
