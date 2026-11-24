export type ThemePref = "light" | "dark" | "system";

/** Runs before the first paint. The account cookie wins over a stale device mirror. */
export const THEME_BOOT = `(function(){try{var c=(document.cookie.match(/(?:^|; )rio_theme=(light|dark|system)/)||[])[1];var p=c||localStorage.getItem("rio-theme");if(p!=="light"&&p!=="dark")p="system";var dark=window.matchMedia("(prefers-color-scheme: dark)").matches;var d=p==="dark"||(p==="system"&&dark);var r=document.documentElement;r.dataset.theme=d?"dark":"light";r.dataset.themePref=p;}catch(e){document.documentElement.dataset.theme="light";}})();`;

export function isThemePref(value: unknown): value is ThemePref {
  return value === "light" || value === "dark" || value === "system";
}

function prefFromCookie(): ThemePref | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )rio_theme=(light|dark|system)/);
  return match && isThemePref(match[1]) ? match[1] : null;
}

export function readPref(): ThemePref {
  try {
    const cookie = prefFromCookie();
    if (cookie) return cookie;
    const stored = localStorage.getItem("rio-theme");
    return isThemePref(stored) ? stored : "system";
  } catch {
    return "system";
  }
}

function writeThemeCookie(pref: ThemePref) {
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `rio_theme=${pref}; Path=/; Max-Age=34560000; SameSite=Lax${secure}`;
}

export function resolvedTheme(pref: ThemePref): "light" | "dark" {
  if (pref === "dark") return "dark";
  if (pref === "light") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/** fade is the 200ms crossfade. The first correction after load passes false. */
export function applyTheme(pref: ThemePref, fade: boolean) {
  const root = document.documentElement;
  const next = resolvedTheme(pref);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (fade && !reduce) {
    root.classList.add("theme-fade");
    window.setTimeout(() => root.classList.remove("theme-fade"), 220);
  }
  root.dataset.theme = next;
  root.dataset.themePref = pref;
  try {
    localStorage.setItem("rio-theme", pref);
  } catch {
    /* A private window still shows the chosen theme for this visit. */
  }
  try {
    writeThemeCookie(pref);
  } catch {
    /* The paint already used the account value for this visit. */
  }
}
