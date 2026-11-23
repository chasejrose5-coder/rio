"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent, type RefObject } from "react";
import { REGIONS, regionById } from "@/lib/stretch-content";
import { BACK_EXTRAS, FRONT_EXTRAS, REGION_OF } from "@/lib/body-regions";
import { expandDrawn, midlineOf, type Drawn } from "@/lib/body-symmetry";
import { backMuscles, backOutline, frontMuscles, frontOutline, type MusclePaths } from "./body-map/paths";

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

type Anchor = { label: string; region: string; x: number; y: number; side: "left" | "right" };

/** Each point sits on that muscle. A column keeps every label at its muscle's height, so the lines stay straight. */
const FRONT_ANCHORS: Anchor[] = [
  { label: "Neck", region: "neck", x: 334, y: 292, side: "left" },
  { label: "Abs / core", region: "abs", x: 320, y: 540, side: "left" },
  { label: "Adductors", region: "adductors", x: 310, y: 690, side: "left" },
  { label: "Hip flexors", region: "hip-flexors", x: 332, y: 880, side: "left" },
  { label: "Shins", region: "shins", x: 278, y: 1100, side: "left" },
  { label: "Shoulders / chest", region: "shoulders", x: 468, y: 360, side: "right" },
  { label: "Quads", region: "quads", x: 404, y: 800, side: "right" },
  { label: "IT band", region: "it-band", x: 466, y: 890, side: "right" },
  { label: "Calves", region: "calves", x: 452, y: 1150, side: "right" },
  { label: "Feet & ankles", region: "feet", x: 432, y: 1324, side: "right" },
];

const BACK_ANCHORS: Anchor[] = [
  { label: "Neck", region: "neck", x: 1048, y: 272, side: "left" },
  { label: "Upper back", region: "upper-back", x: 1004, y: 440, side: "left" },
  { label: "Lower back", region: "lower-back", x: 1016, y: 568, side: "left" },
  { label: "Glutes", region: "glutes", x: 1004, y: 700, side: "left" },
  { label: "Hamstrings", region: "hamstrings", x: 1032, y: 870, side: "left" },
  { label: "Shoulders / chest", region: "shoulders", x: 1224, y: 352, side: "right" },
  { label: "Adductors", region: "adductors", x: 1122, y: 824, side: "right" },
  { label: "IT band", region: "it-band", x: 1186, y: 900, side: "right" },
  { label: "Calves", region: "calves", x: 1168, y: 1140, side: "right" },
  { label: "Feet & ankles", region: "feet", x: 1172, y: 1330, side: "right" },
];

const FRONT_COLUMN = { left: 36, right: 708 };
const BACK_COLUMN = { left: 748, right: 1424 };

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

function columnYs(ys: number[], gap: number) {
  const placed = [...ys];
  for (let index = 1; index < placed.length; index += 1) {
    placed[index] = Math.max(placed[index], placed[index - 1] + gap);
  }
  return placed;
}

/** CSS pixels on this SVG scale with the viewBox, so 14px of type needs a larger user-unit size. */
function useLabelUnits(svg: RefObject<SVGSVGElement | null>, viewBoxWidth: number) {
  const [units, setUnits] = useState(28);
  useEffect(() => {
    const element = svg.current;
    if (!element) return;
    const apply = () => {
      const width = element.getBoundingClientRect().width;
      if (width < 8) return;
      setUnits((20 * viewBoxWidth) / width);
    };
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(element);
    return () => observer.disconnect();
  }, [svg, viewBoxWidth]);
  return units;
}

function Leaders({ rows, columns, fontSize }: { rows: Anchor[]; columns: { left: number; right: number }; fontSize: number }) {
  const gap = fontSize * 2.15;
  const placed: { anchor: Anchor; y: number }[] = [];
  for (const side of ["left", "right"] as const) {
    const group = rows.filter((row) => row.side === side).sort((a, b) => a.y - b.y);
    const ys = columnYs(
      group.map((row) => row.y),
      gap,
    );
    group.forEach((anchor, index) => placed.push({ anchor, y: ys[index] }));
  }
  return (
    <g className="rio-leader" aria-hidden="true" pointerEvents="none" fontSize={fontSize}>
      {placed.map(({ anchor, y }) => {
        const tx = columns[anchor.side];
        const x2 = anchor.side === "left" ? tx + fontSize * 0.4 : tx - fontSize * 0.4;
        return (
          <g key={`${anchor.region}-${anchor.side}`}>
            <line x1={anchor.x} y1={anchor.y} x2={x2} y2={y} />
            <text x={tx} y={y + fontSize * 0.32} textAnchor={anchor.side === "left" ? "end" : "start"}>
              {anchor.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function MirroredPaths({
  drawn,
  fill,
  className,
  regionId,
  leftClip,
  rightClip,
}: {
  drawn: Drawn[];
  fill: string;
  className?: string;
  regionId?: string;
  leftClip: string;
  rightClip: string;
}) {
  return (
    <>
      {drawn.map((part, index) => (
        <path
          key={`${part.place}-${index}-${part.d.slice(0, 16)}`}
          className={className}
          d={part.d}
          fill={fill}
          data-region={regionId}
          clipPath={part.place === "cross" ? leftClip : part.place === "cross-mirror" ? rightClip : undefined}
        />
      ))}
    </>
  );
}

function regionAt(svg: SVGSVGElement, clientX: number, clientY: number): string | null {
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const matrix = svg.getScreenCTM();
  if (!matrix) return null;
  const local = point.matrixTransform(matrix.inverse());
  const paths = [...svg.querySelectorAll<SVGPathElement>("path[data-region]")].reverse();
  for (const path of paths) {
    const region = path.dataset.region;
    if (!region) continue;
    if (path.isPointInFill(local) || path.isPointInStroke(local)) return region;
  }
  return null;
}

function Figure({
  view,
  outline,
  muscles,
  extras,
  anchors,
  columns,
  viewBox,
  viewBoxWidth,
  selected,
  onPick,
}: {
  view: "front" | "back";
  outline: string;
  muscles: readonly MusclePaths[];
  extras: Extra[];
  anchors: Anchor[];
  columns: { left: number; right: number };
  viewBox: string;
  viewBoxWidth: number;
  selected: string | null;
  onPick: (id: string) => void;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const fontSize = useLabelUnits(svg, viewBoxWidth);
  const clip = useId().replace(/:/g, "");
  const leftClip = `url(#${clip}l)`;
  const rightClip = `url(#${clip}r)`;
  const { groups, plain } = collect(muscles, extras);
  const mid = midlineOf(outline);
  const outlineDrawn = expandDrawn([outline], mid);
  const plainBySlug = new Map<string, string[]>();
  for (const part of plain) {
    const list = plainBySlug.get(part.slug) ?? [];
    list.push(part.d);
    plainBySlug.set(part.slug, list);
  }
  const plainDrawn = [...plainBySlug.entries()].map(([slug, paths]) => ({ slug, drawn: expandDrawn(paths, mid) }));
  return (
    <svg
      ref={svg}
      className="rio-body"
      viewBox={viewBox}
      role="group"
      aria-label={view === "front" ? "Front of the body" : "Back of the body"}
      data-testid={view === "front" ? "body-front" : "body-back"}
      onClick={(event) => {
        const region = regionAt(event.currentTarget, event.clientX, event.clientY);
        if (region) onPick(region);
      }}
    >
      <defs>
        <clipPath id={`${clip}l`}>
          <rect x={mid - 4000} y={-2000} width={4001} height={5000} />
        </clipPath>
        <clipPath id={`${clip}r`}>
          <rect x={mid - 1} y={-2000} width={4000} height={5000} />
        </clipPath>
      </defs>
      <MirroredPaths drawn={outlineDrawn} fill={PAPER} className="rio-body-outline" leftClip={leftClip} rightClip={rightClip} />
      {plainDrawn.map((part) => (
        <MirroredPaths key={part.slug} drawn={part.drawn} fill={PAPER} className="rio-body-plain" leftClip={leftClip} rightClip={rightClip} />
      ))}
      {[...groups.entries()].map(([regionId, parts]) => {
        const region = regionById(regionId);
        if (!region) return null;
        const on = selected === regionId;
        const bySlug = new Map<string, string[]>();
        for (const part of parts) {
          const list = bySlug.get(part.slug) ?? [];
          list.push(part.d);
          bySlug.set(part.slug, list);
        }
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
            {[...bySlug.entries()].map(([slug, paths]) => (
              <MirroredPaths
                key={slug}
                drawn={expandDrawn(paths, mid)}
                fill={SLUG_FILL[slug] || region.color}
                regionId={regionId}
                leftClip={leftClip}
                rightClip={rightClip}
              />
            ))}
          </g>
        );
      })}
      <Leaders rows={anchors} columns={columns} fontSize={fontSize} />
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
          anchors={FRONT_ANCHORS}
          columns={FRONT_COLUMN}
          viewBox={narrow ? "150 110 430 1260" : "-280 80 1400 1300"}
          viewBoxWidth={narrow ? 430 : 1400}
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
          anchors={BACK_ANCHORS}
          columns={BACK_COLUMN}
          viewBox={narrow ? "860 110 460 1260" : "430 80 1420 1300"}
          viewBoxWidth={narrow ? 460 : 1420}
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

