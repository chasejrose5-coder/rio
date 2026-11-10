/** About lines. The sentences live in about-copy.ts, generated from Streamlit. */

import { ABOUT } from "./about-copy";

export { ABOUT };

export function visibleAboutLines(): string[] {
  const lines: string[] = [ABOUT.heading, ABOUT.credit];
  for (const section of ABOUT.sections) {
    lines.push(section.title, ...section.visible);
    for (const row of section.rows) lines.push(row.label, row.line);
    lines.push(...section.closing);
  }
  return lines;
}

export function hiddenAboutLines(): string[] {
  return ABOUT.sections.flatMap((section) => [...section.hidden]);
}
