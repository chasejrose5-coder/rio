import { PRIVATE_PREFIXES } from "./public-routes.ts";

/** Signed-in HTML must not sit in a shared cache or the back-forward cache. */
export const PRIVATE_CACHE = "private, no-store";

export function privateNoStoreRoutes(): { source: string; headers: { key: string; value: string }[] }[] {
  const headers = [{ key: "Cache-Control", value: PRIVATE_CACHE }];
  const routes: { source: string; headers: { key: string; value: string }[] }[] = [];
  for (const prefix of PRIVATE_PREFIXES) {
    if (prefix === "/api") continue;
    routes.push({ source: prefix, headers });
    routes.push({ source: `${prefix}/:path*`, headers });
  }
  return routes;
}
