/** Settings copy and the season file. The plan is not rebuilt here. */

export const APP_VERSION = "0.1";

export const TIME_ZONES = [
  "UTC",
  "Pacific/Honolulu",
  "America/Anchorage",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Denver",
  "America/Chicago",
  "America/New_York",
  "America/Sao_Paulo",
  "Europe/London",
  "Europe/Paris",
  "Europe/Berlin",
  "Africa/Johannesburg",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
  "Pacific/Auckland",
] as const;

const DROP = new Set(["probability", "readiness", "readiness_score"]);

export function zoneOptions(saved: string): string[] {
  const listed = TIME_ZONES as readonly string[];
  if (saved && !listed.includes(saved)) return [saved, ...TIME_ZONES];
  return [...TIME_ZONES];
}

/** A display name. Blank is not a name. The same bounds as the account file. */
export function normalizeName(value: string): string | null {
  const text = value.trim().replace(/\s+/g, " ");
  if (!text || text.length > 40) return null;
  if ([...text].some((char) => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)) return null;
  if (![...text].some((char) => /\p{L}/u.test(char))) return null;
  if (![...text].every((char) => /\p{L}/u.test(char) || " '-.".includes(char))) return null;
  return text;
}

export function shownName(name: string, preferred: string): string {
  const nick = preferred.trim().replace(/\s+/g, " ");
  if (nick) return nick;
  return name.trim().replace(/\s+/g, " ");
}

export function nameNote(kind: string): string {
  if (kind === "hosted") return "First name is enough. Saved to your RIO account.";
  return "First name is enough. Saved on this machine.";
}

export function browserClearNote(kind: string): string {
  if (kind === "hosted") return "Signs you out on this browser. Your season stays in your account.";
  return "Clears this browser. The account stays on this machine.";
}

type ExportBody = {
  inputs: {
    current_time: string;
    start_date: string;
    goal_time: string;
    goal_date: string;
  };
  plan?: unknown;
  marks?: unknown;
  actuals?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function dropScores(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(dropScores);
  if (!isRecord(value)) return value;
  const out: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    if (DROP.has(key)) continue;
    out[key] = dropScores(item);
  }
  return out;
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (!isRecord(value)) return value;
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(value).sort()) out[key] = sortValue(value[key]);
  return out;
}

/** The season file Settings downloads. The four inputs are on the object. */
export function seasonFile(body: ExportBody): string {
  const payload = {
    actuals: isRecord(body.actuals) ? body.actuals : {},
    current_time: body.inputs.current_time,
    goal_date: body.inputs.goal_date,
    goal_time: body.inputs.goal_time,
    marks: isRecord(body.marks) ? body.marks : {},
    season: dropScores(body.plan) ?? {},
    start_date: body.inputs.start_date,
  };
  return JSON.stringify(sortValue(payload), null, 2);
}

export function downloadText(filename: string, text: string): void {
  const blob = new Blob([text], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
