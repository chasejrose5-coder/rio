"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { LoadingScreen } from "./LoadingScreen";
import { afterSignIn, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { destinationAfterSignIn, warmDestinationReads } from "@/lib/enter";
import { clearGoogleReturn, takeGoogleReturn } from "@/lib/google-auth";

export function GoogleCallback() {
  const router = useRouter();
  const { refresh } = useAuth();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const back = takeGoogleReturn(window.location.search, window.location.hash);
    if (window.location.search || window.location.hash) {
      window.history.replaceState({}, "", "/auth/callback");
    }
    const fail = (key: "google-failed" | "session-stuck") => {
      clearGoogleReturn();
      router.replace(`/sign-in?note=${key}`);
    };
    if (back.error || !back.code) {
      fail("google-failed");
      return;
    }
    void (async () => {
      try {
        await api.googleFinish(back.code, back.flow);
        warmDestinationReads();
        const signedIn = await refresh();
        const stuck = afterSignIn(signedIn);
        if (stuck) {
          fail("session-stuck");
          return;
        }
        clearGoogleReturn();
        router.replace(await destinationAfterSignIn(signedIn!));
      } catch (caught) {
        fail("google-failed");
      }
    })();
  }, [refresh, router]);

  return <LoadingScreen label="Signing in" />;
}
