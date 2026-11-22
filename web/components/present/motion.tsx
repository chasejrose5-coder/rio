"use client";

import type { PointerEvent } from "react";

/**
 * Names the pressed element as the shared hero for the next navigation.
 * About and Creators are not named, so they do not carry the hero.
 */
export function shareHero(event: PointerEvent<HTMLElement>) {
  document.querySelectorAll<HTMLElement>("[data-rio-share]").forEach((node) => {
    node.style.viewTransitionName = "";
  });
  event.currentTarget.dataset.rioShare = "true";
  event.currentTarget.style.viewTransitionName = "rio-hero";
}
