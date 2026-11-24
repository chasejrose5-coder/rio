import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

/** WCAG relative luminance, 0 to 1. */
function channel(value: number): number {
  const s = value / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const raw = hex.replace("#", "");
  const r = channel(parseInt(raw.slice(0, 2), 16));
  const g = channel(parseInt(raw.slice(2, 4), 16));
  const b = channel(parseInt(raw.slice(4, 6), 16));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(fg: string, bg: string): number {
  const a = luminance(fg);
  const b = luminance(bg);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

const light = {
  paper: "#F4F1EC",
  surface: "#FFFCF7",
  raised: "#FFFFFF",
  ink: "#121110",
  ink2: "#5F5B55",
  ink3: "#6E6A64",
  accent: "#E25A32",
  accentText: "#A63C1A",
  success: "#2F6B3A",
  danger: "#B3261E",
  button: "#C2461F",
  buttonHover: "#A63C1A",
  lineInput: "#8F887E",
  nav: "#121110",
  onNav: "#F4F1EC",
  white: "#FFFFFF",
  easy: "#3F7D4A",
  speed: "#C2461F",
  long: "#23395B",
};

const dark = {
  paper: "#141211",
  surface: "#1E1B19",
  raised: "#282421",
  ink: "#F4F1EC",
  ink2: "#C4BDB3",
  ink3: "#A39B91",
  accent: "#F2794F",
  accentText: "#FF9A72",
  success: "#7CC48A",
  danger: "#FF8F86",
  button: "#C2461F",
  buttonHover: "#A63C1A",
  lineInput: "#7A7168",
  nav: "#0B0A09",
  onNav: "#F4F1EC",
  white: "#FFFFFF",
  easy: "#5FA86B",
  speed: "#E9683F",
  long: "#7E9FDB",
};

const pairs: Array<[string, string, string, number]> = [
  ["ink on paper", "ink", "paper", 4.5],
  ["ink-2 on paper", "ink2", "paper", 4.5],
  ["ink-3 on paper", "ink3", "paper", 4.5],
  ["ink on surface", "ink", "surface", 4.5],
  ["ink-2 on surface", "ink2", "surface", 4.5],
  ["ink-3 on surface", "ink3", "surface", 4.5],
  ["ink on raised", "ink", "raised", 4.5],
  ["ink-2 on raised", "ink2", "raised", 4.5],
  ["ink-3 on raised", "ink3", "raised", 4.5],
  ["accent text on paper", "accentText", "paper", 4.5],
  ["success on paper", "success", "paper", 4.5],
  ["danger on paper", "danger", "paper", 4.5],
  ["accent on paper", "accent", "paper", 3],
  ["accent text on surface", "accentText", "surface", 4.5],
  ["success on surface", "success", "surface", 4.5],
  ["danger on surface", "danger", "surface", 4.5],
  ["white on button", "white", "button", 4.5],
  ["line-input on raised", "lineInput", "raised", 3],
  ["on-nav on nav", "onNav", "nav", 4.5],
  ["easy on surface", "easy", "surface", 3],
  ["speed on surface", "speed", "surface", 3],
  ["long on surface", "long", "surface", 3],
];

function hardcodedInk(css: string): string[] {
  const hits: string[] = [];
  let skipping = false;
  let depth = 0;
  css.split("\n").forEach((line, index) => {
    if (!skipping && /:root\b/.test(line) && line.includes("{")) skipping = true;
    if (skipping) {
      depth += (line.match(/\{/g) || []).length;
      depth -= (line.match(/\}/g) || []).length;
      if (depth <= 0) {
        skipping = false;
        depth = 0;
      }
      return;
    }
    if (/color:\s*#121110/i.test(line)) hits.push(`${index + 1}: ${line.trim()}`);
  });
  return hits;
}

test("signed-in text does not hard-code the light ink", () => {
  for (const name of ["globals.css", "enhance.css", "legal.css"]) {
    const css = readFileSync(new URL(`../app/${name}`, import.meta.url), "utf8");
    assert.deepEqual(hardcodedInk(css), [], name);
  }
});

test("light and dark token pairs meet WCAG AA", () => {
  const misses: string[] = [];
  for (const theme of [light, dark] as const) {
    const name = theme === light ? "light" : "dark";
    for (const [label, fg, bg, need] of pairs) {
      const found = ratio(theme[fg as keyof typeof theme], theme[bg as keyof typeof theme]);
      if (found < need) misses.push(`${name} ${label} ${found.toFixed(2)} < ${need}`);
    }
  }
  assert.deepEqual(misses, []);
});
