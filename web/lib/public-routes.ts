/** Pages a signed-out visitor can read. Everything else is the signed-in app. */

export const PUBLIC_PATHS = [
  "/",
  "/about",
  "/sign-in",
  "/create-account",
  "/forgot-password",
  "/reset-password",
  "/update-password",
  "/confirm",
  "/privacy",
  "/terms",
] as const;

export function isPublicPath(pathname: string): boolean {
  const path = pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname || "/";
  return (PUBLIC_PATHS as readonly string[]).includes(path);
}

/** Prefixes crawlers should skip. /about, /privacy, and /terms stay public. */
export const PRIVATE_PREFIXES = [
  "/activity",
  "/admin",
  "/api",
  "/core",
  "/creators",
  "/decisions",
  "/easy-pace",
  "/foam",
  "/goal",
  "/guide",
  "/heart-rate",
  "/home",
  "/intro",
  "/last-session",
  "/ledger",
  "/library",
  "/more",
  "/next",
  "/past-seasons",
  "/plan",
  "/profile",
  "/recovery",
  "/session",
  "/settings",
  "/start",
  "/strava",
  "/stretch",
] as const;
