/** Which hostnames still get a link to the live site.

The production build is the same on www.riorunning.com and on the old
Vercel hosts. The note is decided from the request host. It is not a redirect.
*/

export const LIVE_ORIGIN = "https://www.riorunning.com";
export const LIVE_LABEL = "riorunning.com";

const CURRENT_HOSTS = new Set([
  "www.riorunning.com",
  "riorunning.com",
  "localhost",
  "127.0.0.1",
  "::1",
]);

/** The hostname from a Host or X-Forwarded-Host value. Empty when it is blank. */
export function hostnameOf(value: string | null | undefined): string {
  if (typeof value !== "string") return "";
  let text = value.trim().toLowerCase();
  if (!text) return "";
  const comma = text.indexOf(",");
  if (comma !== -1) text = text.slice(0, comma).trim();
  if (!text) return "";
  if (text.includes("://")) {
    try {
      text = new URL(text).hostname;
    } catch {
      return "";
    }
  } else if (text.startsWith("[")) {
    const end = text.indexOf("]");
    text = end === -1 ? text.slice(1) : text.slice(1, end);
  } else {
    const colon = text.lastIndexOf(":");
    if (colon > -1 && text.indexOf(":") === colon) text = text.slice(0, colon);
  }
  if (text.endsWith(".")) text = text.slice(0, -1);
  return text;
}

/**
 * The host the browser opened. X-Forwarded-Host wins when a proxy sets it,
 * which is how a custom domain stays distinct from an old Vercel hostname.
 */
export function requestHostname(
  forwardedHost: string | null | undefined,
  host: string | null | undefined,
): string {
  const forwarded = hostnameOf(forwardedHost);
  if (forwarded) return forwarded;
  return hostnameOf(host);
}

/** True for an old public host. The live site and a laptop stay quiet. */
export function isLegacyHost(hostname: string | null | undefined): boolean {
  const name = hostnameOf(hostname);
  if (!name) return false;
  return !CURRENT_HOSTS.has(name);
}
