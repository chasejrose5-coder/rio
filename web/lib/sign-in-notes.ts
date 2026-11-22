import { SESSION_STUCK } from "./api.ts";

/** Known return notes. Inherited keys such as __proto__ are not notes. */
export const SIGN_IN_NOTES: Record<string, string> = {
  "password-updated": "Password updated. Log in with the new one.",
  "google-failed": "Google sign-in could not be finished. Try again.",
  "session-stuck": SESSION_STUCK,
};

export function signInNotice(note: string | null | undefined): string {
  if (!note || !Object.hasOwn(SIGN_IN_NOTES, note)) return "";
  return SIGN_IN_NOTES[note];
}
