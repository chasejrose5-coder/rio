"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PageSkeleton } from "./PageSkeleton";
import { LoadingScreen } from "./LoadingScreen";
import { Splash } from "./Splash";
import { useAuth } from "@/lib/auth";
import { destinationAfterSignIn } from "@/lib/enter";

const SPLASH_KEY = "rio_startup_seen";

function splashSkipped(): boolean {
  if (window.sessionStorage.getItem(SPLASH_KEY) === "1") return true;
  return new URLSearchParams(window.location.search).get("skip") === "1";
}

export function Gate() {
  const { status, athlete, refresh } = useAuth();
  const router = useRouter();
  const [splash, setSplash] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [seasonProblem, setSeasonProblem] = useState(false);

  useEffect(() => {
    if (status === "unreachable" || status === "loading") return;
    if (status === "out") {
      if (!splashSkipped()) return;
      if (window.sessionStorage.getItem(SPLASH_KEY) !== "1") {
        window.sessionStorage.setItem(SPLASH_KEY, "1");
      }
      router.replace("/sign-in?skip=1");
      return;
    }
    if (!athlete) return;
    let live = true;
    void destinationAfterSignIn(athlete)
      .then((path) => {
        if (live) router.replace(path);
      })
      .catch(() => {
        if (live) setSeasonProblem(true);
      });
    return () => {
      live = false;
    };
  }, [status, athlete, router, attempt]);

  if (status === "unreachable") {
    return <LoadingScreen label="Starting the server" onRetry={() => void refresh()} />;
  }
  if (seasonProblem) {
    return (
      <div className="rio-gate-retry">
        <p className="rio-error">The season could not be loaded.</p>
        <button
          type="button"
          className="rio-primary"
          onClick={() => {
            setSeasonProblem(false);
            setAttempt((current) => current + 1);
          }}
        >
          Retry
        </button>
      </div>
    );
  }
  if (status === "in") return <PageSkeleton variant="home" />;
  if (!splash) return <PageSkeleton variant="home" />;
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
