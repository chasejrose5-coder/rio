/** Continue with Google. The button stays off until the public flag is set.

The flag is not a secret. The Google client secret stays in Supabase.
*/

export const GOOGLE_FAILED = "Google sign-in could not be finished. Try again.";
export const GOOGLE_START_FAILED = "Google sign-in could not be started. Try email instead.";

const STASH = "rio-google-return";

export function googleAuthEnabled(raw: string | undefined = process.env.NEXT_PUBLIC_GOOGLE_AUTH_ENABLED): boolean {
  const text = (raw ?? "").trim().toLowerCase();
  return text === "1" || text === "true";
}

/** The API's authorize URL, or "" when it does not point at Supabase Google. */
export function googleAuthorizeUrl(raw: string): string {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return "";
  }
  if (!url.pathname.endsWith("/auth/v1/authorize")) return "";
  if (url.searchParams.get("provider") !== "google") return "";
  const host = url.hostname;
  const local = host === "localhost" || host === "127.0.0.1";
  if (url.protocol === "https:" && (host.endsWith(".supabase.co") || local)) return url.toString();
  if (url.protocol === "http:" && local) return url.toString();
  return "";
}

export type GoogleReturn = {
  code: string;
  flow: string;
  error: string;
};

function paramsOf(raw: string): URLSearchParams {
  const text = raw.startsWith("?") || raw.startsWith("#") ? raw.slice(1) : raw;
  return new URLSearchParams(text);
}

export function googleReturn(search: string, hash: string): GoogleReturn {
  const query = paramsOf(search);
  const fragment = paramsOf(hash);
  const pick = (name: string) => query.get(name) || fragment.get(name) || "";
  return {
    code: pick("code"),
    flow: pick("flow"),
    error: pick("error") || pick("error_description"),
  };
}

function readStash(): GoogleReturn | null {
  if (typeof sessionStorage === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STASH);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<GoogleReturn>;
    if (!parsed || typeof parsed !== "object") return null;
    return {
      code: typeof parsed.code === "string" ? parsed.code : "",
      flow: typeof parsed.flow === "string" ? parsed.flow : "",
      error: typeof parsed.error === "string" ? parsed.error : "",
    };
  } catch {
    return null;
  }
}

function writeStash(back: GoogleReturn): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.setItem(STASH, JSON.stringify(back));
  } catch {
    /* A blocked store still finishes this attempt from the URL. */
  }
}

/** The code on this URL, or the one stashed when a strict-mode remount cleared it. */
export function takeGoogleReturn(search: string, hash: string): GoogleReturn {
  const fromUrl = googleReturn(search, hash);
  if (fromUrl.code || fromUrl.error) {
    writeStash(fromUrl);
    return fromUrl;
  }
  return readStash() ?? fromUrl;
}

export function clearGoogleReturn(): void {
  if (typeof sessionStorage === "undefined") return;
  try {
    sessionStorage.removeItem(STASH);
  } catch {
    /* The next visit to this path has no code of its own. */
  }
}
