"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { ApiError, afterSignIn, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { destinationAfterSignIn } from "@/lib/enter";
import { GOOGLE_FAILED, googleNoncePair } from "@/lib/google-auth";

const SCRIPT = "https://accounts.google.com/gsi/client";

type CredentialResponse = { credential?: string };

type GoogleId = {
  initialize: (config: {
    client_id: string;
    callback: (response: CredentialResponse) => void;
    nonce: string;
    auto_select: boolean;
    use_fedcm_for_prompt: boolean;
  }) => void;
  renderButton: (parent: HTMLElement, options: Record<string, string | number | boolean>) => void;
  cancel: () => void;
};

declare global {
  interface Window {
    google?: { accounts?: { id?: GoogleId } };
  }
}

function loadGsi(): Promise<void> {
  const ready = window.google?.accounts?.id;
  if (ready) return Promise.resolve();
  const found = document.querySelector(`script[src="${SCRIPT}"]`);
  if (found) {
    return new Promise((resolve, reject) => {
      found.addEventListener("load", () => resolve(), { once: true });
      found.addEventListener("error", () => reject(new Error("gis")), { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("gis"));
    document.head.appendChild(script);
  });
}

export function GoogleIdentityButton({
  clientId,
  onError,
  onFail,
}: {
  clientId: string;
  onError: (message: string) => void;
  onFail: () => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { refresh } = useAuth();
  const onErrorRef = useRef(onError);
  const onFailRef = useRef(onFail);

  useEffect(() => {
    onErrorRef.current = onError;
    onFailRef.current = onFail;
  }, [onError, onFail]);

  useEffect(() => {
    const parent = host.current;
    if (!parent) return;
    let cancel = false;
    void (async () => {
      const pair = await googleNoncePair();
      if (cancel) return;
      await loadGsi();
      const gis = window.google?.accounts?.id;
      if (cancel || !gis) throw new Error("gis");
      gis.initialize({
        client_id: clientId,
        nonce: pair.hashed,
        auto_select: false,
        use_fedcm_for_prompt: false,
        callback: (response) => {
          const token = response.credential || "";
          if (!token) {
            onErrorRef.current(GOOGLE_FAILED);
            return;
          }
          void (async () => {
            try {
              await api.googleIdToken(token, pair.raw);
              const signedIn = await refresh();
              const stuck = afterSignIn(signedIn);
              if (stuck) {
                onErrorRef.current(stuck);
                return;
              }
              router.replace(await destinationAfterSignIn(signedIn!));
            } catch (caught) {
              onErrorRef.current(caught instanceof ApiError ? caught.message : GOOGLE_FAILED);
            }
          })();
        },
      });
      if (cancel) return;
      parent.replaceChildren();
      const width = Math.max(200, Math.min(400, Math.floor(parent.clientWidth || 320)));
      gis.renderButton(parent, {
        type: "standard",
        theme: "outline",
        size: "large",
        text: "continue_with",
        shape: "pill",
        width,
        logo_alignment: "center",
      });
    })().catch(() => {
      if (!cancel) onFailRef.current();
    });
    return () => {
      cancel = true;
      window.google?.accounts?.id?.cancel();
    };
  }, [clientId, refresh, router]);

  return <div className="rio-google-slot" ref={host} />;
}
