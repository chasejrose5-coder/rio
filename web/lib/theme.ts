export type ThemePref = "light" | "dark" | "system";

/** Runs before the first paint. Keep this string in sync with applyTheme. */
export const THEME_BOOT = `(function(){try{var p=localStorage.getItem("rio-theme");if(p!=="light"&&p!=="dark")p="system";var dark=window.matchMedia("(prefers-color-scheme: dark)").matches;var d=p==="dark"||(p==="system"&&dark);var r=document.documentElement;r.dataset.theme=d?"dark":"light";r.dataset.themePref=p;}catch(e){document.documentElement.dataset.theme="light";}})();`;

export function isThemePref(value: unknown): value is ThemePref {
  return value === "light" || value === "dark" || value === "system";
}

export function readPref(): ThemePref {
  try {
    const stored = localStorage.getItem("rio-theme");
    return isThemePref(stored) ? stored : "system";
  } catch {
    return "system";
  }
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
}
