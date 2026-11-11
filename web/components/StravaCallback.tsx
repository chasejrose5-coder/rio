"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { LoadingScreen } from "./LoadingScreen";
import { ApiError, api } from "@/lib/api";

export function StravaCallback() {
  const params = useSearchParams();
  const router = useRouter();
  const [problem, setProblem] = useState("");

  useEffect(() => {
    const code = params.get("code") || "";
    const state = params.get("state") || "";
    if (!code || !state) {
      router.replace("/settings?strava=error");
      return;
    }
    void api
      .stravaCallback(code, state)
      .then(() => router.replace("/settings?strava=connected"))
      .catch((caught) => {
        setProblem(caught instanceof ApiError ? caught.message : "Strava could not be connected.");
        router.replace("/settings?strava=error");
      });
  }, [params, router]);

  return (
    <>
      <LoadingScreen label="Connecting Strava" />
      {problem ? <p className="rio-error">{problem}</p> : null}
    </>
  );
}
