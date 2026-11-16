type Seg =
  | { c: "M" | "L"; x: number; y: number }
  | { c: "C"; x1: number; y1: number; x2: number; y2: number; x: number; y: number }
  | { c: "Q"; x1: number; y1: number; x: number; y: number }
  | { c: "A"; rx: number; ry: number; rot: number; large: number; sweep: number; x: number; y: number }
  | { c: "Z" };

type Raw =
  | { c: "M" | "L" | "T"; rel: boolean; x: number; y: number }
  | { c: "H"; rel: boolean; x: number }
  | { c: "V"; rel: boolean; y: number }
  | { c: "C"; rel: boolean; x1: number; y1: number; x2: number; y2: number; x: number; y: number }
  | { c: "S"; rel: boolean; x2: number; y2: number; x: number; y: number }
  | { c: "Q"; rel: boolean; x1: number; y1: number; x: number; y: number }
  | { c: "A"; rel: boolean; rx: number; ry: number; rot: number; large: number; sweep: number; x: number; y: number }
  | { c: "Z" };

export type Drawn = { d: string; place: "left" | "right" | "cross" | "cross-mirror" };

function parse(d: string): Raw[] {
  let i = 0;
  const s = d.trim();
  const skip = () => {
    while (i < s.length && /[\s,]/.test(s[i])) i += 1;
  };
  const num = () => {
    skip();
    const start = i;
    if (s[i] === "+" || s[i] === "-") i += 1;
    let dot = false;
    while (i < s.length) {
      const ch = s[i];
      if (ch >= "0" && ch <= "9") i += 1;
      else if (ch === "." && !dot) {
        dot = true;
        i += 1;
      } else break;
    }
    if (s[i] === "e" || s[i] === "E") {
      i += 1;
      if (s[i] === "+" || s[i] === "-") i += 1;
      while (s[i] >= "0" && s[i] <= "9") i += 1;
    }
    return Number(s.slice(start, i));
  };
  const flag = () => {
    skip();
    const ch = s[i];
    i += 1;
    return ch === "1" ? 1 : 0;
  };
  const segs: Raw[] = [];
  let cmd = "";
  while (i < s.length) {
    skip();
    if (i >= s.length) break;
    if (/[a-zA-Z]/.test(s[i])) cmd = s[i++];
    const rel = cmd === cmd.toLowerCase();
    const kind = cmd.toUpperCase();
    if (kind === "Z") {
      segs.push({ c: "Z" });
      continue;
    }
    if (kind === "M" || kind === "L" || kind === "T") segs.push({ c: kind, rel, x: num(), y: num() });
    else if (kind === "H") segs.push({ c: "H", rel, x: num() });
    else if (kind === "V") segs.push({ c: "V", rel, y: num() });
    else if (kind === "C") segs.push({ c: "C", rel, x1: num(), y1: num(), x2: num(), y2: num(), x: num(), y: num() });
    else if (kind === "S") segs.push({ c: "S", rel, x2: num(), y2: num(), x: num(), y: num() });
    else if (kind === "Q") segs.push({ c: "Q", rel, x1: num(), y1: num(), x: num(), y: num() });
    else if (kind === "A") segs.push({ c: "A", rel, rx: num(), ry: num(), rot: num(), large: flag(), sweep: flag(), x: num(), y: num() });
    skip();
    if (i < s.length && !/[a-zA-Z]/.test(s[i]) && kind === "M") cmd = rel ? "l" : "L";
  }
  return segs;
}

function absolute(segs: Raw[]): Seg[] {
  let cx = 0;
  let cy = 0;
  let sx = 0;
  let sy = 0;
  const out: Seg[] = [];
  for (const g of segs) {
    if (g.c === "Z") {
      out.push({ c: "Z" });
      cx = sx;
      cy = sy;
      continue;
    }
    const X = (x: number) => (g.rel ? cx + x : x);
    const Y = (y: number) => (g.rel ? cy + y : y);
    if (g.c === "M") {
      cx = X(g.x);
      cy = Y(g.y);
      sx = cx;
      sy = cy;
      out.push({ c: "M", x: cx, y: cy });
    } else if (g.c === "L") {
      cx = X(g.x);
      cy = Y(g.y);
      out.push({ c: "L", x: cx, y: cy });
    } else if (g.c === "H") {
      cx = X(g.x);
      out.push({ c: "L", x: cx, y: cy });
    } else if (g.c === "V") {
      cy = Y(g.y);
      out.push({ c: "L", x: cx, y: cy });
    } else if (g.c === "C") {
      const x1 = X(g.x1);
      const y1 = Y(g.y1);
      const x2 = X(g.x2);
      const y2 = Y(g.y2);
      const x = X(g.x);
      const y = Y(g.y);
      out.push({ c: "C", x1, y1, x2, y2, x, y });
      cx = x;
      cy = y;
    } else if (g.c === "S") {
      const x2 = X(g.x2);
      const y2 = Y(g.y2);
      const x = X(g.x);
      const y = Y(g.y);
      out.push({ c: "C", x1: cx, y1: cy, x2, y2, x, y });
      cx = x;
      cy = y;
    } else if (g.c === "Q") {
      const x1 = X(g.x1);
      const y1 = Y(g.y1);
      const x = X(g.x);
      const y = Y(g.y);
      out.push({ c: "Q", x1, y1, x, y });
      cx = x;
      cy = y;
    } else if (g.c === "T") {
      const x = X(g.x);
      const y = Y(g.y);
      out.push({ c: "Q", x1: cx, y1: cy, x, y });
      cx = x;
      cy = y;
    } else if (g.c === "A") {
      const x = X(g.x);
      const y = Y(g.y);
      out.push({ c: "A", rx: g.rx, ry: g.ry, rot: g.rot, large: g.large, sweep: g.sweep, x, y });
      cx = x;
      cy = y;
    }
  }
  return out;
}

function bounds(segs: Seg[]) {
  let minx = Infinity;
  let maxx = -Infinity;
  let miny = Infinity;
  let maxy = -Infinity;
  for (const g of segs) {
    if (g.c === "Z") continue;
    for (const x of g.c === "C" ? [g.x1, g.x2, g.x] : g.c === "Q" ? [g.x1, g.x] : [g.x]) {
      minx = Math.min(minx, x);
      maxx = Math.max(maxx, x);
    }
    for (const y of g.c === "C" ? [g.y1, g.y2, g.y] : g.c === "Q" ? [g.y1, g.y] : [g.y]) {
      miny = Math.min(miny, y);
      maxy = Math.max(maxy, y);
    }
  }
  return { minx, maxx, miny, maxy };
}

function round(n: number) {
  return Math.round(n * 100) / 100;
}

function serialize(segs: Seg[]) {
  return segs
    .map((g) => {
      if (g.c === "Z") return "Z";
      if (g.c === "M" || g.c === "L") return `${g.c}${round(g.x)} ${round(g.y)}`;
      if (g.c === "C") return `C${round(g.x1)} ${round(g.y1)} ${round(g.x2)} ${round(g.y2)} ${round(g.x)} ${round(g.y)}`;
      if (g.c === "Q") return `Q${round(g.x1)} ${round(g.y1)} ${round(g.x)} ${round(g.y)}`;
      if (g.c === "A") return `A${round(g.rx)} ${round(g.ry)} ${round(g.rot)} ${g.large} ${g.sweep} ${round(g.x)} ${round(g.y)}`;
      return "";
    })
    .join("");
}

function canonical(d: string) {
  return serialize(absolute(parse(d)));
}

function mirrorSegs(segs: Seg[], mid: number): Seg[] {
  const mx = (x: number) => 2 * mid - x;
  return segs.map((g) => {
    if (g.c === "Z") return g;
    if (g.c === "M" || g.c === "L") return { ...g, x: mx(g.x) };
    if (g.c === "C") return { ...g, x1: mx(g.x1), x2: mx(g.x2), x: mx(g.x) };
    if (g.c === "Q") return { ...g, x1: mx(g.x1), x: mx(g.x) };
    if (g.c === "A") return { c: "A" as const, rx: g.rx, ry: g.ry, rot: -g.rot, large: g.large, sweep: g.sweep ? 0 : 1, x: mx(g.x), y: g.y };
    return g;
  });
}

export function mirrorPath(d: string, mid: number) {
  return serialize(mirrorSegs(absolute(parse(d)), mid));
}

export function samePath(a: string, b: string) {
  return canonical(a) === canonical(b);
}

function sideOf(d: string, mid: number): "left" | "right" | "cross" {
  const box = bounds(absolute(parse(d)));
  if (box.maxx <= mid + 0.75) return "left";
  if (box.minx >= mid - 0.75) return "right";
  return "cross";
}

/** Keep one side of each path and add its exact mirror, so both sides match. */
export function expandDrawn(paths: readonly string[], mid: number): Drawn[] {
  const left: string[] = [];
  const right: string[] = [];
  const cross: string[] = [];
  for (const d of paths) {
    const side = sideOf(d, mid);
    if (side === "left") left.push(canonical(d));
    else if (side === "right") right.push(canonical(d));
    else cross.push(canonical(d));
  }
  const source = left.length ? left : right.map((d) => mirrorPath(d, mid));
  return [
    ...source.map((d) => ({ d, place: "left" as const })),
    ...source.map((d) => ({ d: mirrorPath(d, mid), place: "right" as const })),
    ...cross.map((d) => ({ d, place: "cross" as const })),
    ...cross.map((d) => ({ d: mirrorPath(d, mid), place: "cross-mirror" as const })),
  ];
}

export function midlineOf(d: string) {
  const box = bounds(absolute(parse(d)));
  return (box.minx + box.maxx) / 2;
}
