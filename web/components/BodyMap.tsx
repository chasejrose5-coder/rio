"use client";

import { useEffect, useState, type KeyboardEvent } from "react";
import { REGIONS, regionById } from "@/lib/stretch-content";
import { backMuscles, backOutline, frontMuscles, frontOutline, type MusclePaths } from "./body-map/paths";

/** Library slugs grouped into the sore-spot areas. Unlisted slugs stay as the white outline. */
const REGION_OF: Record<string, string | null> = {
  chest: "shoulders",
  deltoids: "shoulders",
  trapezius: "upper-back",
  "upper-back": "upper-back",
  neck: "neck",
  abs: "abs",
  obliques: "abs",
  quadriceps: "quads",
  adductors: "adductors",
  tibialis: "shins",
  calves: "calves",
  feet: "feet",
  ankles: "feet",
  hamstring: "hamstrings",
  gluteal: "glutes",
  "lower-back": "lower-back",
  biceps: null,
  triceps: null,
  forearm: null,
  hands: null,
  knees: null,
  head: null,
  hair: null,
};

/** Soft pastels. One color per muscle, several muscles can share a sore-spot button. */
const SLUG_FILL: Record<string, string> = {
  chest: "#f4a8b0",
  deltoids: "#f6d56a",
  trapezius: "#d7b4ea",
  "upper-back": "#9ed6a0",
  neck: "#e7c8f4",
  abs: "#c5e6a0",
  obliques: "#8fce8f",
  quadriceps: "#f3b0b6",
  adductors: "#a8d8a8",
  tibialis: "#9fd4ee",
  calves: "#7ec4e6",
  feet: "#f6c89a",
  ankles: "#f3d2a4",
  hamstring: "#f0a0a8",
  gluteal: "#c9b0ea",
  "lower-back": "#f6e08a",
  "hip-flexors": "#f6d98a",
  "it-band": "#f0b86a",
  shoulders: "#f6d56a",
  quads: "#f3b0b6",
  shins: "#9fd4ee",
  hamstrings: "#f0a0a8",
  glutes: "#c9b0ea",
};

const PAPER = "#fffcf8";

type Extra = { region: string; paths: string[] };

/** The source set has no hip-flexor or outer-hip path. These sit in the same outline style. */
const FRONT_EXTRAS: Extra[] = [
  {
    region: "hip-flexors",
    paths: [
      "M322 748 C306 786 314 860 348 888 C376 856 370 784 350 748 Z",
      "M398 748 C380 786 406 862 442 888 C470 856 462 784 430 748 Z",
    ],
  },
  {
    region: "it-band",
    paths: [
      "M252 800 C244 850 248 930 260 980 L284 968 C290 900 284 840 272 800 Z",
      "M472 800 C480 850 476 930 464 980 L440 968 C434 900 440 840 452 800 Z",
    ],
  },
];

const BACK_EXTRAS: Extra[] = [
  {
    region: "it-band",
    paths: [
      "M976 800 C968 850 972 930 984 980 L1008 968 C1014 900 1008 840 996 800 Z",
      "M1196 800 C1204 850 1200 930 1188 980 L1164 968 C1158 900 1164 840 1176 800 Z",
    ],
  },
];

type Leader = {
  label: string;
  region: string;
  x: number;
  y: number;
  tx: number;
  ty: number;
  side: "left" | "right";
  /** A bend keeps the line under the outstretched hand. */
  bend?: { x: number; y: number };
};

const FRONT_LEADERS: Leader[] = [
  { label: "Neck", region: "neck", x: 360, y: 300, tx: -30, ty: 280, side: "left" },
  { label: "Abs / core", region: "abs", x: 300, y: 540, tx: -30, ty: 540, side: "left" },
  { label: "Hip flexors", region: "hip-flexors", x: 341, y: 850, tx: -30, ty: 870, side: "left" },
  { label: "Adductors", region: "adductors", x: 318, y: 735, tx: -30, ty: 1000, side: "left", bend: { x: 240, y: 1000 } },
  { label: "Shins", region: "shins", x: 280, y: 1100, tx: -30, ty: 1140, side: "left" },
  { label: "Shoulders / chest", region: "shoulders", x: 450, y: 330, tx: 760, ty: 260, side: "right" },
  { label: "Quads", region: "quads", x: 420, y: 880, tx: 760, ty: 1040, side: "right" },
  { label: "IT band", region: "it-band", x: 464, y: 890, tx: 760, ty: 900, side: "right" },
  { label: "Calves", region: "calves", x: 450, y: 1160, tx: 760, ty: 1160, side: "right" },
  { label: "Feet & ankles", region: "feet", x: 430, y: 1320, tx: 760, ty: 1300, side: "right" },
];

const BACK_LEADERS: Leader[] = [
  { label: "Neck", region: "neck", x: 1060, y: 300, tx: 700, ty: 270, side: "left" },
  { label: "Upper back", region: "upper-back", x: 1080, y: 450, tx: 700, ty: 400, side: "left" },
  { label: "Lower back", region: "lower-back", x: 1070, y: 560, tx: 700, ty: 860, side: "left", bend: { x: 990, y: 860 } },
  { label: "Glutes", region: "glutes", x: 1060, y: 720, tx: 700, ty: 980, side: "left", bend: { x: 990, y: 980 } },
  { label: "Hamstrings", region: "hamstrings", x: 1000, y: 870, tx: 700, ty: 1100, side: "left" },
  { label: "Shoulders / chest", region: "shoulders", x: 1220, y: 330, tx: 1500, ty: 270, side: "right" },
  { label: "Adductors", region: "adductors", x: 1104, y: 810, tx: 1500, ty: 920, side: "right", bend: { x: 1280, y: 920 } },
  { label: "IT band", region: "it-band", x: 1178, y: 890, tx: 1500, ty: 1020, side: "right" },
  { label: "Calves", region: "calves", x: 1160, y: 1124, tx: 1500, ty: 1160, side: "right" },
  { label: "Feet & ankles", region: "feet", x: 1160, y: 1320, tx: 1500, ty: 1320, side: "right" },
];

function useNarrow() {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(max-width: 860px)");
    const apply = () => setNarrow(query.matches);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);
  return narrow;
}

function onKey(event: KeyboardEvent, pick: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    pick();
  }
}

function collect(muscles: readonly MusclePaths[], extras: Extra[]) {
  const groups = new Map<string, { slug: string; d: string }[]>();
  const plain: { slug: string; d: string }[] = [];
  for (const muscle of muscles) {
    const region = REGION_OF[muscle.slug] ?? null;
    for (const d of muscle.paths) {
      if (!region) {
        plain.push({ slug: muscle.slug, d });
        continue;
      }
      const list = groups.get(region) ?? [];
      list.push({ slug: muscle.slug, d });
      groups.set(region, list);
    }
  }
  for (const extra of extras) {
    const list = groups.get(extra.region) ?? [];
    for (const d of extra.paths) list.push({ slug: extra.region, d });
    groups.set(extra.region, list);
  }
  return { groups, plain };
}

function Leaders({ rows }: { rows: Leader[] }) {
  return (
    <g className="rio-leader" aria-hidden="true" pointerEvents="none">
      {rows.map((row) => {
        const textX = row.tx + (row.side === "left" ? 8 : -8);
        const points = row.bend
          ? `${row.x},${row.y} ${row.bend.x},${row.bend.y} ${textX},${row.ty - 4}`
          : "";
        return (
          <g key={`${row.region}-${row.side}`}>
            {row.bend ? (
              <polyline points={points} fill="none" />
            ) : (
              <line x1={row.x} y1={row.y} x2={textX} y2={row.ty - 4} />
            )}
            <text x={row.tx} y={row.ty} textAnchor={row.side === "left" ? "end" : "start"}>
              {row.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function Figure({
  view,
  outline,
  muscles,
  extras,
  leaders,
  viewBox,
  selected,
  onPick,
}: {
  view: "front" | "back";
  outline: string;
  muscles: readonly MusclePaths[];
  extras: Extra[];
  leaders: Leader[];
  viewBox: string;
  selected: string | null;
  onPick: (id: string) => void;
}) {
  const { groups, plain } = collect(muscles, extras);
  return (
    <svg
      className="rio-body"
      viewBox={viewBox}
      role="group"
      aria-label={view === "front" ? "Front of the body" : "Back of the body"}
      data-testid={view === "front" ? "body-front" : "body-back"}
    >
      <path className="rio-body-outline" d={outline} />
      {plain.map((part) => (
        <path key={`${part.slug}-${part.d.slice(0, 24)}`} className="rio-body-plain" d={part.d} fill={PAPER} />
      ))}
      {[...groups.entries()].map(([regionId, parts]) => {
        const region = regionById(regionId);
        if (!region) return null;
        const on = selected === regionId;
        return (
          <g
            key={regionId}
            className={on ? "rio-region is-selected" : "rio-region"}
            role="button"
            tabIndex={0}
            aria-label={`${region.label}, ${view} view`}
            aria-pressed={on}
            onClick={() => onPick(regionId)}
            onKeyDown={(event) => onKey(event, () => onPick(regionId))}
          >
            {parts.map((part) => (
              <path key={`${part.slug}-${part.d.slice(0, 28)}`} d={part.d} fill={SLUG_FILL[part.slug] || region.color} />
            ))}
          </g>
        );
      })}
      <Leaders rows={leaders} />
    </svg>
  );
}

function Legend({ onPick, selected }: { onPick: (id: string) => void; selected: string | null }) {
  return (
    <ul className="rio-body-legend">
      {REGIONS.map((region) => {
        const on = selected === region.id;
        return (
          <li key={region.id}>
            <button type="button" aria-pressed={on} onClick={() => onPick(region.id)}>
              <span className="rio-swatch" style={{ background: SLUG_FILL[region.id] || region.color }} aria-hidden="true" />
              {region.label}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** Front and back outlines from react-native-body-highlighter, grouped into sore-spot areas. */
export function BodyMap({ selected, onPick }: { selected: string | null; onPick: (id: string) => void }) {
  const narrow = useNarrow();
  return (
    <div className="rio-bodies">
      <figure>
        <figcaption>Front</figcaption>
        <Figure
          view="front"
          outline={frontOutline}
          muscles={frontMuscles}
          extras={FRONT_EXTRAS}
          leaders={FRONT_LEADERS}
          viewBox={narrow ? "150 110 430 1260" : "-280 80 1400 1360"}
          selected={selected}
          onPick={onPick}
        />
      </figure>
      <figure>
        <figcaption>Back</figcaption>
        <Figure
          view="back"
          outline={backOutline}
          muscles={backMuscles}
          extras={BACK_EXTRAS}
          leaders={BACK_LEADERS}
          viewBox={narrow ? "860 110 460 1260" : "420 80 1480 1360"}
          selected={selected}
          onPick={onPick}
        />
      </figure>
      <Legend selected={selected} onPick={onPick} />
      <p className="rio-body-credit">Body outlines: react-native-body-highlighter (MIT) by HichamELBSI</p>
      <p className="rio-sr">{REGIONS.length} areas. Each area can be reached from the keyboard.</p>
    </div>
  );
}

