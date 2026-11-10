"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Splash } from "./Splash";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { landingPath } from "@/lib/landing";
import type { Athlete, CurrentSeason } from "@/lib/types";

const SPLASH_KEY = "rio_startup_seen";

function splashSkipped(): boolean {
  if (window.sessionStorage.getItem(SPLASH_KEY) === "1") return true;
  return new URLSearchParams(window.location.search).get("skip") === "1";
}

export function needsEasyPace(athlete: Athlete | null): boolean {
  return !String(athlete?.prefs?.easy_pace || "").trim();
}

export function needsIntro(athlete: Athlete | null, season: CurrentSeason | null): boolean {
  if (athlete?.prefs?.intro_seen === true) return false;
  if (athlete?.prefs?.intro_seen === false) return true;
  return season == null;
}

export function Gate() {
  const { status, athlete, refresh } = useAuth();
  const router = useRouter();
  const [splash, setSplash] = useState(false);

  useEffect(() => {
    if (status === "loading") return;
    if (status === "out") {
      if (!splashSkipped()) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setSplash(true);
        return;
      }
      if (window.sessionStorage.getItem(SPLASH_KEY) !== "1") {
        window.sessionStorage.setItem(SPLASH_KEY, "1");
      }
      router.replace("/sign-in?skip=1");
      return;
    }
    let live = true;
    void api.currentSeason().then(async (season) => {
      if (!live) return;
      if (needsEasyPace(athlete)) {
        router.replace("/easy-pace");
        return;
      }
      if (needsIntro(athlete, season)) {
        router.replace("/intro");
        return;
      }
      if (season && athlete?.prefs?.intro_seen !== true) {
        try {
          await api.patchSettings({ intro_seen: true });
          await refresh();
        } catch {
          /* A missed flag still opens Home. The guide can show next time. */
        }
      }
      if (live) router.replace(landingPath(season));
    });
    return () => {
      live = false;
    };
  }, [status, athlete, refresh, router]);

  if (splash) {
    return (
      <Splash
        onContinue={() => {
          window.sessionStorage.setItem(SPLASH_KEY, "1");
          setSplash(false);
          if (status === "out") router.replace("/sign-in?skip=1");
        }}
      />
    );
  }
  return <p className="rio-wait">Loading</p>;
}
