"use client";

import { Footer, PhotoCredit } from "./Footer";

export function Splash({ onContinue }: { onContinue: () => void }) {
  return (
    <div className="rio-splash">
      <section className="rio-splash-copy">
        <p className="rio-brand-mark">RIO</p>
        <p className="rio-brand-owned">Runner Intelligence Owned</p>
        <h1>Your Race, Your Plan, Your Result</h1>
        <p className="rio-reason-line">Every rep has a reason</p>
        <blockquote>
          <p>“Most plans tell you what to run. RIO shows you why, and adjusts when the season doesn&apos;t go to script.”</p>
          <p className="rio-founder-by">— Chase Rose, Founder</p>
        </blockquote>
        <button type="button" className="rio-primary rio-splash-go" onClick={onContinue}>
          Continue
        </button>
      </section>
      <PhotoCredit onPhoto>Photo by Giant Asparagus on Pexels</PhotoCredit>
      <Footer onPhoto />
    </div>
  );
}
