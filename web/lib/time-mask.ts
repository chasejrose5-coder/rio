/** Start's 800 times. Digits become m:ss.cc. 202 is 2:02, then 2:02.00. */

const RACE = /^(\d):(\d{2})(?:\.(\d{1,2}))?$/;

export function maskRaceTime(raw: string): string {
  if (/[^\d:.]/.test(raw)) return raw;
  const digits = raw.replace(/\D/g, "").slice(0, 5);
  if (!digits) return "";
  const minute = digits[0] ?? "";
  const rest = digits.slice(1);
  if (!rest) return minute;
  const seconds = rest.slice(0, 2);
  const fraction = rest.slice(2);
  const text = `${minute}:${seconds}`;
  return fraction ? `${text}.${fraction}` : text;
}

/** Pad a finished m:ss so the field matches 2:02.00. A tenth becomes hundredths: 2:02.5 is 2:02.50. */
export function commitRaceTime(raw: string): string {
  const masked = maskRaceTime(raw);
  const match = RACE.exec(masked);
  if (!match) return masked;
  const fraction = match[3] ?? "";
  if (fraction.length === 2) return masked;
  return `${match[1]}:${match[2]}.${fraction.padEnd(2, "0")}`;
}

export function raceTimeError(value: string): string {
  const match = /^(\d):(\d{2})\.(\d{2})$/.exec(value);
  if (!match) return "Enter a time like 2:02.00.";
  const seconds = Number(match[2]);
  const hundredths = Number(match[3]);
  if (seconds >= 60) return "Enter a time like 2:02.00.";
  if (Number(match[1]) * 60 + seconds + hundredths / 100 <= 0) return "Enter a time like 2:02.00.";
  return "";
}

/** Reps such as 400 m. Extra digits become seconds.hundredths, like 50.90. */
export function maskRepTime(raw: string): string {
  if (/[^\d.]/.test(raw)) return raw;
  const digits = raw.replace(/\D/g, "").slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, digits.length - 2)}.${digits.slice(-2)}`;
}
