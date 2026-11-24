"use client";

import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { applyTheme, isThemePref, readPref } from "@/lib/theme";

/** After the account loads, its theme wins over the device mirror. No crossfade on that correction. */
export function ThemeSync() {
  const { athlete } = useAuth();

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (document.documentElement.dataset.themePref === "system") applyTheme("system", false);
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const account = athlete?.prefs.theme;
    if (!isThemePref(account)) return;
    if (readPref() === account && document.documentElement.dataset.themePref === account) return;
    applyTheme(account, false);
  }, [athlete]);

  return null;
}
