/** Library labels. The menu itself stays on GET /library. */

export function countLabel(count: number): string {
  const noun = count === 1 ? "workout" : "workouts";
  return `${count} ${noun}`;
}

export function capacityClass(family: string): string {
  const token = family.toLowerCase().replace(/[^a-z0-9_]/g, "");
  return token ? `rio-lib-cap rio-cap rio-cap-${token}` : "rio-lib-cap rio-cap";
}
