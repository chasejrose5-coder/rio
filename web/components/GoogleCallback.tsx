"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { LoadingScreen } from "./LoadingScreen";
import { ApiError, afterSignIn, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { destinationAfterSignIn } from "@/lib/enter";
import { GOOGLE_FAILED, clearGoogleReturn, takeGoogleReturn } from "@/lib/google-auth";

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
    const fail = (message: string) => {
      clearGoogleReturn();
      router.replace(`/sign-in?note=${encodeURIComponent(message)}`);
    };
    if (back.error || !back.code) {
      fail(GOOGLE_FAILED);
      return;
    }
    void (async () => {
      try {
        await api.googleFinish(back.code, back.flow);
        const signedIn = await refresh();
        const stuck = afterSignIn(signedIn);
        if (stuck) {
          fail(stuck);
          return;
        }
        clearGoogleReturn();
        router.replace(await destinationAfterSignIn(signedIn!));
      } catch (caught) {
        fail(caught instanceof ApiError ? caught.message : GOOGLE_FAILED);
      }
    })();
  }, [refresh, router]);

  return <LoadingScreen label="Signing in" />;
}
