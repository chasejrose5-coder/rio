"use client";

import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ABOUT } from "@/lib/about";
import { useAuth } from "@/lib/auth";

export function AboutView() {
  return (
    <RequireUser>
      <AboutBody />
    </RequireUser>
  );
}

function AboutBody() {
  const { athlete } = useAuth();
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);
  const compact = athlete?.prefs.compact === true;

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "about";
    window.sessionStorage.setItem(key, "about");
    if (first) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setArm(true);
    }
  }, []);

  useEffect(() => {
    if (!arm) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRise(true);
    const timer = window.setTimeout(() => setRise(false), 280);
    return () => window.clearTimeout(timer);
  }, [arm]);

  return (
    <div className={compact ? "page-about is-compact" : "page-about"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-about-banner">
          <div className="rio-about-shade" aria-hidden="true" />
          <div className="rio-about-title">
            <p className="rio-index rio-index-light">About</p>
            <h1>{ABOUT.heading}</h1>
          </div>
          <p className="rio-photo-credit">{ABOUT.credit}</p>
        </header>
        {ABOUT.sections.map((section) => (
          <section key={section.title} className="rio-card">
            <p className="rio-mark-label">{section.title}</p>
            {section.visible.map((paragraph, index) =>
              index === 0 ? (
                <p key={paragraph} className="rio-note">
                  {paragraph}
                </p>
              ) : (
                <p key={paragraph} className="rio-prose">
                  {paragraph}
                </p>
              ),
            )}
            {section.rows.length > 0 ? (
              <div className="rio-fields">
                {section.rows.map((row) => (
                  <div key={row.label} className="rio-field">
                    <div className="rio-k">{row.label}</div>
                    <div className="rio-v">{row.line}</div>
                  </div>
                ))}
              </div>
            ) : null}
            {section.closing.map((paragraph) => (
              <p key={paragraph} className="rio-prose">
                {paragraph}
              </p>
            ))}
            {section.hidden.length > 0 ? (
              <div hidden>
                {section.hidden.map((paragraph) => (
                  <p key={paragraph} className="rio-prose">
                    {paragraph}
                  </p>
                ))}
              </div>
            ) : null}
          </section>
        ))}
        <Footer />
      </main>
    </div>
  );
}
