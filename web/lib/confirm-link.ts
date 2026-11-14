/** Tokens on a Supabase confirmation link.

Signup and email-change mail open /confirm. The same names as a reset link
are accepted in the query or the hash. The query wins when both name a value.
`token_hash` wins over `token`. A recovery fragment belongs on /reset-password.
*/

export type ConfirmLink = {
  token: string;
  accessToken: string;
  refreshToken: string;
  type: string;
  error: string;
  errorCode: string;
};

export type ConfirmRead = "ready" | "invalid" | "missing" | "rate" | "recovery";

const KINDS = new Set(["signup", "email", "email_change"]);

function paramsOf(raw: string): URLSearchParams {
  const text = raw.startsWith("?") || raw.startsWith("#") ? raw.slice(1) : raw;
  return new URLSearchParams(text);
}

function first(query: URLSearchParams, fragment: URLSearchParams, name: string): string {
  return query.get(name) || fragment.get(name) || "";
}

export function confirmFromLocation(search: string, hash: string): ConfirmLink {
  const query = paramsOf(search);
  const fragment = paramsOf(hash);
  return {
    token: first(query, fragment, "token_hash") || first(query, fragment, "token"),
    accessToken: first(query, fragment, "access_token"),
    refreshToken: first(query, fragment, "refresh_token"),
    type: first(query, fragment, "type"),
    error: first(query, fragment, "error"),
    errorCode: first(query, fragment, "error_code"),
  };
}

export function confirmRead(link: ConfirmLink): ConfirmRead {
  const code = `${link.error} ${link.errorCode}`.toLowerCase();
  if (code.trim()) {
    if (
      code.includes("rate") ||
      code.includes("too many") ||
      code.includes("over_email") ||
      code.includes("over_request")
    ) {
      return "rate";
    }
    return "invalid";
  }
  if (link.type === "recovery") return "recovery";
  const typed = KINDS.has(link.type);
  if (link.token && typed) return "ready";
  if (typed && link.accessToken && link.refreshToken) return "ready";
  if (!link.token && !link.accessToken && !link.refreshToken && !link.type) return "missing";
  return "invalid";
}
