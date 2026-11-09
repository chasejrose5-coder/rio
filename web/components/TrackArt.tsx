function n(value: number): string {
  return value.toFixed(2);
}

function semiRight(cx: number, cy: number, radius: number): string {
  return `A ${n(radius)} ${n(radius)} 0 0 1 ${n(cx + radius)} ${n(cy)} A ${n(radius)} ${n(radius)} 0 0 1 ${n(cx)} ${n(cy + radius)} `;
}

function bendUp(cx: number, cy: number, radius: number, sweep: string): string {
  const side = sweep === "0" ? 1 : -1;
  return `A ${n(radius)} ${n(radius)} 0 0 ${sweep} ${n(cx + side * radius)} ${n(cy)} A ${n(radius)} ${n(radius)} 0 0 ${sweep} ${n(cx)} ${n(cy - radius)} `;
}

function bendDown(cx: number, cy: number, radius: number, sweep: string): string {
  const side = sweep === "1" ? 1 : -1;
  return `A ${n(radius)} ${n(radius)} 0 0 ${sweep} ${n(cx + side * radius)} ${n(cy)} A ${n(radius)} ${n(radius)} 0 0 ${sweep} ${n(cx)} ${n(cy + radius)} `;
}

/** Eight lanes. The home straight runs out to the left. Display only. */
export function TrackArt() {
  const lanes = 8;
  const outer = 168;
  const inner = outer * (47.4 / 95.5);
  const lane = (outer - inner) / lanes;
  const straight = outer * (117.6 / 95.5);
  const vbX = 36;
  const vbY = -6;
  const vbW = 726;
  const vbH = 388;
  const cy = 18 + outer;
  const mid = vbX + vbW / 2;
  const lx = mid - straight / 2;
  const rx = lx + straight;
  const leftEnd = lx - outer;
  const infield = `M ${n(lx)} ${n(cy - inner)} H ${n(rx)} ${semiRight(rx, cy, inner)}H ${n(lx)} ${bendUp(lx, cy, inner, "1")}Z`;
  const shell = `M ${n(lx)} ${n(cy - outer)} H ${n(rx)} ${semiRight(rx, cy, outer)}H ${n(leftEnd)} V ${n(cy)} A ${n(outer)} ${n(outer)} 0 0 1 ${n(lx)} ${n(cy - outer)} Z`;
  const lines = [];
  for (let index = 0; index <= lanes; index += 1) {
    const radius = inner + lane * index;
    lines.push(
      `M ${n(leftEnd)} ${n(cy + radius)} H ${n(rx)} ${bendUp(rx, cy, radius, "0")}H ${n(lx)} ${bendDown(lx, cy, radius, "0")}`,
    );
  }
  return (
    <svg className="rio-track-svg" viewBox={`${vbX} ${vbY} ${vbW} ${vbH}`} aria-hidden="true">
      <path fill="currentColor" fillRule="evenodd" d={`${shell} ${infield}`} />
      {lines.map((d) => (
        <path key={d} fill="none" stroke="#fff" strokeOpacity={0.9} strokeWidth={1.35} d={d} />
      ))}
    </svg>
  );
}
