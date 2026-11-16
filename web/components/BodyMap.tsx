"use client";

import type { KeyboardEvent } from "react";
import { REGIONS, regionById } from "@/lib/stretch-content";

type Shape = { id: string; paths: string[]; ellipses?: { cx: number; cy: number; rx: number; ry: number }[] };

const INK = "#3d4c5e";

const FRONT: Shape[] = [
  {
    id: "shoulders",
    paths: [
      "M52 108 C52 92 74 84 120 84 C166 84 188 92 188 108 L180 176 C172 194 150 202 120 202 C90 202 68 194 60 176 Z",
      "M70 114 C48 124 36 160 42 196 C54 206 68 198 66 180 C56 150 58 128 78 116 Z",
      "M170 114 C192 124 204 160 198 196 C186 206 172 198 174 180 C184 150 182 128 162 116 Z",
    ],
  },
  { id: "abs", paths: ["M86 206 H154 L148 252 H92 Z"] },
  { id: "hip-flexors", paths: ["M78 258 H162 L156 304 H84 Z"] },
  { id: "it-band", paths: ["M58 310 H74 L70 402 H54 Z", "M166 310 H182 L186 402 H170 Z"] },
  { id: "quads", paths: ["M76 310 H104 L100 404 H72 Z", "M136 310 H164 L168 404 H140 Z"] },
  { id: "adductors", paths: ["M106 316 H120 L116 400 H108 Z", "M134 316 H120 L124 400 H132 Z"] },
  { id: "shins", paths: ["M74 410 H104 L98 474 H70 Z", "M136 410 H166 L170 474 H142 Z"] },
  { id: "feet", paths: ["M62 480 H112 L116 508 H58 Z", "M128 480 H178 L182 508 H124 Z"] },
  { id: "neck", paths: ["M104 62 H136 V96 H104 Z"] },
];

const BACK: Shape[] = [
  {
    id: "upper-back",
    paths: ["M90 100 C96 90 108 86 120 86 C132 86 144 90 150 100 L156 198 C148 214 136 220 120 220 C104 220 92 214 84 198 Z"],
  },
  {
    id: "shoulders",
    paths: [
      "M86 112 C60 124 50 162 62 198 C76 186 88 158 96 120 Z",
      "M154 112 C180 124 190 162 178 198 C164 186 152 158 144 120 Z",
    ],
  },
  { id: "lower-back", paths: ["M90 224 H150 L144 270 H96 Z"] },
  {
    id: "glutes",
    paths: [],
    ellipses: [
      { cx: 98, cy: 308, rx: 30, ry: 34 },
      { cx: 142, cy: 308, rx: 30, ry: 34 },
    ],
  },
  { id: "it-band", paths: ["M58 346 H74 L70 438 H54 Z", "M166 346 H182 L186 438 H170 Z"] },
  { id: "hamstrings", paths: ["M76 346 H116 L110 440 H72 Z", "M124 346 H164 L168 440 H130 Z"] },
  { id: "calves", paths: ["M76 446 H112 L104 500 H74 Z", "M128 446 H164 L166 500 H136 Z"] },
  { id: "feet", paths: ["M64 506 H116 L120 528 H60 Z", "M124 506 H176 L180 528 H120 Z"] },
  { id: "neck", paths: ["M104 62 H136 V96 H104 Z"] },
];

const FRONT_LEGEND = ["neck", "shoulders", "abs", "hip-flexors", "quads", "adductors", "shins", "feet"];
const BACK_LEGEND = ["upper-back", "lower-back", "glutes", "hamstrings", "calves", "it-band"];

function onKey(event: KeyboardEvent, pick: () => void) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    pick();
  }
}

function Figure({
  view,
  shapes,
  selected,
  onPick,
}: {
  view: "front" | "back";
  shapes: Shape[];
  selected: string | null;
  onPick: (id: string) => void;
}) {
  return (
    <svg className="rio-body" viewBox="0 0 240 560" role="group" aria-label={view === "front" ? "Front of the body" : "Back of the body"} data-testid={view === "front" ? "body-front" : "body-back"}>
      <ellipse cx="120" cy="40" rx="24" ry="28" fill={INK} pointerEvents="none" />
      {shapes.map((shape) => {
        const region = regionById(shape.id);
        if (!region) return null;
        const on = selected === shape.id;
        return (
          <g
            key={`${view}-${shape.id}`}
            role="button"
            tabIndex={0}
            aria-label={`${region.label}, ${view} view`}
            aria-pressed={on}
            className={on ? "is-selected" : undefined}
            onClick={() => onPick(shape.id)}
            onKeyDown={(event) => onKey(event, () => onPick(shape.id))}
          >
            {shape.paths.map((d) => (
              <path key={d} d={d} fill={region.color} />
            ))}
            {shape.ellipses?.map((dot) => (
              <ellipse key={`${dot.cx}-${dot.cy}`} cx={dot.cx} cy={dot.cy} rx={dot.rx} ry={dot.ry} fill={region.color} />
            ))}
          </g>
        );
      })}
      <ellipse cx="34" cy="204" rx="11" ry="13" fill={INK} pointerEvents="none" />
      <ellipse cx="206" cy="204" rx="11" ry="13" fill={INK} pointerEvents="none" />
    </svg>
  );
}

function Legend({ ids, onPick, selected }: { ids: string[]; onPick: (id: string) => void; selected: string | null }) {
  return (
    <ul className="rio-body-legend">
      {ids.map((id) => {
        const region = regionById(id);
        if (!region) return null;
        const on = selected === id;
        return (
          <li key={id}>
            <button type="button" aria-pressed={on} onClick={() => onPick(id)}>
              <span className="rio-swatch" style={{ background: region.color }} aria-hidden="true" />
              {region.label}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** Original front and back figures. The stock chart was a style reference only. */
export function BodyMap({ selected, onPick }: { selected: string | null; onPick: (id: string) => void }) {
  return (
    <div className="rio-bodies">
      <Legend ids={FRONT_LEGEND} selected={selected} onPick={onPick} />
      <figure>
        <figcaption>Front</figcaption>
        <Figure view="front" shapes={FRONT} selected={selected} onPick={onPick} />
      </figure>
      <figure>
        <figcaption>Back</figcaption>
        <Figure view="back" shapes={BACK} selected={selected} onPick={onPick} />
      </figure>
      <Legend ids={BACK_LEGEND} selected={selected} onPick={onPick} />
      <p className="rio-sr">
        {REGIONS.length} areas. Use the list or the figure. Each area can be reached from the keyboard.
      </p>
    </div>
  );
}
