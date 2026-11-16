/** Pages a signed-out visitor can read. Everything else is the signed-in app. */

export const PUBLIC_PATHS = [
  "/",
  "/sign-in",
  "/create-account",
  "/forgot-password",
  "/reset-password",
  "/confirm",
  "/privacy",
  "/terms",
] as const;

/** Prefixes crawlers should skip. /privacy and /terms stay public. */
export const PRIVATE_PREFIXES = [
  "/about",
  "/activity",
  "/admin",
  "/api",
  "/creators",
  "/decisions",
  "/easy-pace",
  "/goal",
  "/guide",
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
  "/session",
  "/settings",
  "/start",
  "/strava",
  "/stretch",
] as const;
