"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Visual save tick driven by the button's existing busy flag. The accessible name stays the original label. */
export function SaveLabel({ busy, error = "", children }: { busy: boolean; error?: string; children: ReactNode }) {
  const face = useRef<HTMLSpanElement>(null);
  const wasBusy = useRef(false);

  useEffect(() => {
    const node = face.current;
    if (!node) return;
    if (busy) {
      wasBusy.current = true;
      node.dataset.face = "saving";
      return;
    }
    if (!wasBusy.current) return;
    wasBusy.current = false;
    if (error) {
      node.dataset.face = "idle";
      return;
    }
    node.dataset.face = "saved";
    const timer = window.setTimeout(() => {
      if (node.dataset.face === "saved") node.dataset.face = "idle";
    }, 1600);
    return () => window.clearTimeout(timer);
  }, [busy, error]);

  return (
    <span className="rio-save-face" ref={face} data-face="idle">
      <span className="rio-save-label">{children}</span>
      <span className="rio-spin" aria-hidden="true" />
      <span className="rio-saved-word" aria-hidden="true">
        <svg className="rio-tick" viewBox="0 0 16 16" aria-hidden="true">
          <path d="M3 8.2 6.2 11.5 13 4.5" />
        </svg>
        Saved
      </span>
    </span>
  );
}

/** Check and Saved beside a field after the existing autosave finishes. */
export function SaveFlash({ busy, error = "" }: { busy: boolean; error?: string }) {
  const face = useRef<HTMLSpanElement>(null);
  const wasBusy = useRef(false);

  useEffect(() => {
    const node = face.current;
    if (!node) return;
    if (busy) {
      wasBusy.current = true;
      node.hidden = true;
      return;
    }
    if (!wasBusy.current || error) {
      wasBusy.current = false;
      node.hidden = true;
      return;
    }
    wasBusy.current = false;
    node.hidden = false;
    const timer = window.setTimeout(() => {
      node.hidden = true;
    }, 1600);
    return () => window.clearTimeout(timer);
  }, [busy, error]);

  return (
    <span className="rio-saved-word rio-saved-inline" ref={face} hidden aria-hidden="true">
      <svg className="rio-tick" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M3 8.2 6.2 11.5 13 4.5" />
      </svg>
      Saved
    </span>
  );
}
