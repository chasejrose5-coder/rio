/** Activity display. Dates follow the Settings zone. Charts are the Streamlit geometry. */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function zoneName(saved: string | undefined, browser: string | undefined): string {
  const chosen = (saved || "").trim();
  if (chosen && zoneOk(chosen)) return chosen;
  const local = (browser || "").trim();
  if (local && zoneOk(local)) return local;
  return "UTC";
}

function zoneOk(zone: string): boolean {
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: zone }).format(0);
    return true;
  } catch {
    return false;
  }
}

/** "Nov 9, 11:30 PM". The epoch is a unix second. The zone is the Settings zone. */
export function formatSynced(when: number, timeZone: string): string {
  const zone = zoneName(timeZone, "");
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hourCycle: "h12",
  }).formatToParts(new Date(when * 1000));
  const read = (type: string) => parts.find((part) => part.type === type)?.value || "";
  const hour = String(Number(read("hour")));
  const minute = read("minute").padStart(2, "0");
  const period = read("dayPeriod").replace(/\./g, "").toUpperCase();
  return `${read("month")} ${read("day")}, ${hour}:${minute} ${period}`;
}

export function syncEpoch(value: number | string | null | undefined): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) return Math.floor(parsed / 1000);
  }
  return null;
}

export function shortDay(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) return iso;
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (month < 1 || month > 12) return iso;
  return `${MONTHS[month - 1]} ${day}`;
}

const CHART_W = 640;
const HEART_H = 220;
const HEART_LEFT = 46;
const HEART_RIGHT = 16;
const HEART_TOP = 16;
const HEART_BOTTOM = 32;

export type HeartDot = { x: number; y: number; date: string; bpm: number; label: string };
export type ChartLabel = { x: number; y: number; text: string; anchor: "start" | "middle" | "end" };

export type HeartChart = {
  width: number;
  height: number;
  left: number;
  top: number;
  plotBottom: number;
  right: number;
  ticks: { y: number; text: string }[];
  dots: HeartDot[];
  dates: ChartLabel[];
};

export function heartChart(points: { date?: string; bpm?: number }[] | undefined): HeartChart | null {
  const dots: { date: string; day: number; bpm: number }[] = [];
  for (const point of points || []) {
    const iso = String(point?.date || "");
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    const bpm = point?.bpm;
    if (!match || typeof bpm !== "number" || !Number.isFinite(bpm) || bpm <= 0) continue;
    const day = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    dots.push({ date: iso.slice(0, 10), day, bpm });
  }
  if (!dots.length) return null;
  dots.sort((a, b) => a.day - b.day || a.bpm - b.bpm);
  const width = CHART_W;
  const height = HEART_H;
  const plotW = width - HEART_LEFT - HEART_RIGHT;
  const plotH = height - HEART_TOP - HEART_BOTTOM;
  const low = Math.min(...dots.map((item) => item.bpm));
  const high = Math.max(...dots.map((item) => item.bpm));
  const floor = high === low ? low - 8 : low - Math.max(4, (high - low) * 0.12);
  const peak = high === low ? high + 8 : high + Math.max(4, (high - low) * 0.12);
  const first = dots[0].day;
  const last = dots[dots.length - 1].day;
  const span = Math.round((last - first) / 86400000) || 1;
  const placed = dots.map((item) => {
    const x = dots.length === 1 ? HEART_LEFT + plotW / 2 : HEART_LEFT + (plotW * Math.round((item.day - first) / 86400000)) / span;
    const y = HEART_TOP + plotH * (1 - (item.bpm - floor) / (peak - floor));
    return { x, y, date: item.date, bpm: item.bpm, label: shortDay(item.date) };
  });
  const ticks = [floor, (floor + peak) / 2, peak].map((value, index) => ({
    y: index === 0 ? HEART_TOP + plotH : index === 1 ? HEART_TOP + plotH / 2 : HEART_TOP,
    text: String(Math.round(value)),
  }));
  return {
    width,
    height,
    left: HEART_LEFT,
    top: HEART_TOP,
    plotBottom: HEART_TOP + plotH,
    right: width - HEART_RIGHT,
    ticks,
    dots: placed,
    dates: thinned(placed, HEART_LEFT, width - HEART_RIGHT, height - 10),
  };
}

function thinned(dots: HeartDot[], left: number, right: number, y: number): ChartLabel[] {
  if (!dots.length) return [];
  const picks = [0];
  if (dots.length > 1) picks.push(dots.length - 1);
  const room = Math.min(6, Math.max(2, Math.floor((right - left) / 72)));
  if (dots.length > 2 && room > 2) {
    const step = (dots.length - 1) / (room - 1);
    for (let index = 1; index < room - 1; index += 1) picks.push(Math.round(index * step));
  }
  const ordered = [...new Set(picks)].sort((a, b) => a - b);
  const chosen: ChartLabel[] = [];
  let lastX: number | null = null;
  ordered.forEach((index, place) => {
    const x = dots[index].x;
    if (lastX !== null && x - lastX < 64 && place !== ordered.length - 1) return;
    chosen.push({ x, y, text: dots[index].label, anchor: "middle" });
    lastX = x;
  });
  const end = dots[dots.length - 1];
  if (chosen.length && chosen[chosen.length - 1].text !== end.label) {
    if (!chosen.length || end.x - chosen[chosen.length - 1].x >= 48) {
      chosen.push({ x: end.x, y, text: end.label, anchor: "middle" });
    } else {
      chosen[chosen.length - 1] = { x: end.x, y, text: end.label, anchor: "middle" };
    }
  }
  return chosen.slice(0, 6);
}

const VOL_W = 640;
const VOL_H = 152;
const VOL_LEFT = 42;
const VOL_RIGHT = 12;
const VOL_TOP = 14;
const VOL_BOTTOM = 24;
const M_TO_MI = 1 / 1609.344;

export type VolumeChart = {
  width: number;
  height: number;
  unit: string;
  guides: { y: number }[];
  line: string;
  highlight: { x: number; y: number } | null;
  alone: { x: number; y: number } | null;
  yLabels: ChartLabel[];
  xLabels: ChartLabel[];
  tips: { x: number; y: number; text: string }[];
};

export function volumeChart(meters: number[], units: string, captions: string[], highlight: number): VolumeChart | null {
  const values = meters.map((value) => {
    if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return 0;
    return Math.round(value);
  });
  if (!values.length) return null;
  const peak = Math.max(...values);
  const unit = units === "miles" ? "mi" : peak >= 1000 ? "km" : "m";
  const count = values.length;
  const width = VOL_W - VOL_LEFT - VOL_RIGHT;
  const height = VOL_H - VOL_TOP - VOL_BOTTOM;
  const baseline = VOL_TOP + height;
  const points = values.map((metersValue, index) => {
    const x = count === 1 ? VOL_LEFT + width / 2 : VOL_LEFT + (width * index) / (count - 1);
    const y = peak <= 0 ? baseline : baseline - height * (metersValue / peak);
    return { x, y };
  });
  const top = Math.min(...points.map((point) => point.y));
  const floor = Math.max(...points.map((point) => point.y));
  const guides = [{ y: floor }];
  if (Math.abs(top - floor) > 1) guides.push({ y: (top + floor) / 2 }, { y: top });
  const yLabels: ChartLabel[] = [];
  const ticks: { amount: number; y: number }[] = [{ amount: 0, y: floor }];
  if (peak > 0) {
    ticks.push({ amount: peak, y: top });
    const mid = peak / 2;
    if (amountText(mid, unit) !== amountText(0, unit) && amountText(mid, unit) !== amountText(peak, unit)) {
      ticks.push({ amount: mid, y: (top + floor) / 2 });
    }
  }
  for (const tick of ticks) {
    yLabels.push({ x: VOL_LEFT - 8, y: tick.y, text: amountText(tick.amount, unit), anchor: "end" });
  }
  const gap = count <= 1 ? width : width / (count - 1);
  let step = 1;
  while (count > 1 && step < count && step * gap < 36) step += 1;
  const indexes = count <= 1 ? [0] : [];
  if (count > 1) {
    for (let index = 0; index < count; index += step) indexes.push(index);
    const last = count - 1;
    if (indexes[indexes.length - 1] !== last) {
      if ((last - indexes[indexes.length - 1]) * gap < 28 && indexes.length > 1) indexes[indexes.length - 1] = last;
      else indexes.push(last);
    }
  }
  const xLabels = indexes.map((index) => {
    const last = count - 1;
    const anchor = index === 0 && count > 1 ? "start" : index === last && count > 1 ? "end" : "middle";
    return { x: points[index].x, y: VOL_H - 8, text: String(index + 1), anchor } as ChartLabel;
  });
  const tips = values.map((metersValue, index) => ({
    x: points[index].x,
    y: points[index].y,
    text: captions[index] || `${amountText(metersValue, unit)} ${unit}`,
  }));
  const mark = highlight >= 0 && highlight < points.length ? points[highlight] : null;
  return {
    width: VOL_W,
    height: VOL_H,
    unit,
    guides,
    line: points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" "),
    highlight: count === 1 ? null : mark,
    alone: count === 1 ? points[0] : null,
    yLabels,
    xLabels,
    tips,
  };
}

function amountText(meters: number, unit: string): string {
  if (meters <= 0) return "0";
  if (unit === "m") return Math.round(meters).toLocaleString("en-US");
  if (unit === "km") {
    const km = meters / 1000;
    return Math.abs(km - Math.round(km)) < 1e-9 ? String(Math.round(km)) : km.toFixed(1);
  }
  const miles = meters * M_TO_MI;
  return miles < 0.1 ? miles.toFixed(2) : miles.toFixed(1);
}

function weekIndex(start: string, length: number, day: string): number {
  const opening = /^(\d{4})-(\d{2})-(\d{2})/.exec(start);
  const current = /^(\d{4})-(\d{2})-(\d{2})/.exec(day);
  if (!opening || !current || length <= 0) return 1;
  const startDate = Date.UTC(Number(opening[1]), Number(opening[2]) - 1, Number(opening[3]));
  const sunday = startDate - new Date(startDate).getUTCDay() * 86400000;
  const dayDate = Date.UTC(Number(current[1]), Number(current[2]) - 1, Number(current[3]));
  if (dayDate < sunday) return 1;
  const number = Math.floor((dayDate - sunday) / 86400000 / 7) + 1;
  if (number > length) return length;
  return Math.max(1, number);
}

export function shownWeeks(meters: number[], start: string, length: number, today: string): { values: number[]; highlight: number } {
  if (!meters.length || !Number.isInteger(length) || length <= 0) return { values: [], highlight: -1 };
  const highlight = Math.min(meters.length, Math.max(weekIndex(start, length, today), 1)) - 1;
  const end = Math.min(meters.length, Math.max(highlight, 0) + 1);
  return { values: meters.slice(0, end), highlight: end - 1 };
}

export const SUMMARY_LABELS = ["Distance", "Runs", "On track", "Ahead", "Behind", "Extra"] as const;

export function summaryTiles(summary: { distance?: string; runs?: number; counts?: Record<string, number> } | undefined): { label: string; value: string }[] {
  const counts = summary?.counts || {};
  return [
    { label: "Distance", value: summary?.distance || "—" },
    { label: "Runs", value: String(summary?.runs || 0) },
    { label: "On track", value: String(counts["On track"] || 0) },
    { label: "Ahead", value: String(counts.Ahead || 0) },
    { label: "Behind", value: String(counts.Behind || 0) },
    { label: "Extra", value: String(counts.Extra || 0) },
  ];
}

export function badgeKind(status: string): string {
  if (status === "On track") return "on-track";
  if (status === "Ahead") return "ahead";
  if (status === "Behind") return "behind";
  return "extra";
}

export function hideBanner(banner: string | null | undefined): boolean {
  const text = (banner || "").toLowerCase();
  return !text || text.includes("synthetic") || text.includes("demo");
}
