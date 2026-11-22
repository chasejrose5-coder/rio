"use client";

import { useEffect, useRef } from "react";
import { Footer, PhotoCredit } from "./Footer";

const GIANT = "https://www.pexels.com/@giantasparagus/";

export function Splash({ onContinue }: { onContinue: () => void }) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = root.current;
    if (!node) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const fine = window.matchMedia("(pointer: fine)").matches;
    const seen = window.sessionStorage.getItem("rio-splash-motion") === "1";
    if (reduce) node.classList.add("is-quiet");
    else if (!seen) node.classList.add("is-entering");
    window.sessionStorage.setItem("rio-splash-motion", "1");
    if (reduce || !fine) return;
    const move = (event: PointerEvent) => {
      const x = (event.clientX / window.innerWidth - 0.5) * 16;
      const y = (event.clientY / window.innerHeight - 0.5) * 16;
      node.style.backgroundPosition = `calc(70% + ${x}px) calc(50% + ${y}px)`;
    };
    window.addEventListener("pointermove", move);
    return () => window.removeEventListener("pointermove", move);
  }, []);

  return (
    <div className="rio-splash" ref={root}>
      <main className="rio-splash-copy">
        <p className="rio-brand-mark">RIO</p>
        <p className="rio-brand-owned">Runner Intelligence Owned</p>
        <h1>Your Race, Your Plan, Your Result</h1>
        <p className="rio-reason-line">Every rep has a reason</p>
        <p>A training plan for any runner, built from your own times.</p>
        <blockquote>
          <p>Most plans tell you what to run. RIO shows you why, and adjusts when the season doesn’t go to script.</p>
        </blockquote>
        <button type="button" className="rio-primary rio-splash-go" onClick={onContinue}>
          Get started
        </button>
        <div className="rio-splash-strip">
          <PhotoCredit onPhoto href={GIANT}>
            Photo by Giant Asparagus on Pexels
          </PhotoCredit>
          <Footer onPhoto />
        </div>
      </main>
    </div>
  );
}
