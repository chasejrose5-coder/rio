/** Same-origin API proxy for the test deploy.

The browser calls `/api/...` on the Next host. Next forwards that to the
FastAPI origin with the `/api` prefix removed. `rio_hosted` stays host-only
(no Domain attribute), so the cookie is set on the Next host, not on Render.

Unset `RIO_API_ORIGIN` leaves the rewrite off. Local dev keeps calling
`http://localhost:8000` directly.
*/

export type ApiRewrite = {
  source: string;
  destination: string;
};

const SOURCE = "/api/:path*";

export function apiOrigin(raw: string | undefined | null): string | null {
  if (typeof raw !== "string") return null;
  const text = raw.trim().replace(/\/$/, "");
  if (!text || text.includes("*") || /[\s\r\n]/.test(text)) return null;
  let url: URL;
  try {
    url = new URL(text);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null;
  if (url.username || url.password || url.search || url.hash) return null;
  if (url.pathname !== "/" && url.pathname !== "") return null;
  if (!url.hostname || url.hostname === "*") return null;
  return url.origin;
}

export function apiProxyRewrites(raw: string | undefined | null): ApiRewrite[] {
  const origin = apiOrigin(raw);
  if (!origin) return [];
  return [{ source: SOURCE, destination: `${origin}/:path*` }];
}

/** The upstream URL a rewrite is expected to call, including the query string. */
export function applyApiRewrite(rewrites: ApiRewrite[], requestPath: string): string | null {
  const rewrite = rewrites.find((item) => item.source === SOURCE);
  if (!rewrite || !rewrite.destination.endsWith("/:path*")) return null;
  const queryAt = requestPath.indexOf("?");
  const path = queryAt === -1 ? requestPath : requestPath.slice(0, queryAt);
  const query = queryAt === -1 ? "" : requestPath.slice(queryAt);
  if (!path.startsWith("/api/")) return null;
  const rest = path.slice("/api/".length);
  if (!rest || rest.startsWith("/") || rest.split("/").includes("..")) return null;
  const origin = rewrite.destination.slice(0, -"/:path*".length);
  return `${origin}/${rest}${query}`;
}
