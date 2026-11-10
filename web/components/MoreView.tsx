"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { useAuth } from "@/lib/auth";
import { MORE_LINKS } from "@/lib/profile";

export function MoreView() {
  return (
    <RequireUser>
      <MoreBody />
    </RequireUser>
  );
}

function MoreBody() {
  const { athlete } = useAuth();
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);
  const compact = athlete?.prefs.compact === true;

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "more";
    window.sessionStorage.setItem(key, "more");
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
    <div className={compact ? "page-more is-compact" : "page-more"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero">
          <h1>More</h1>
          <p className="rio-range">The rest of the season, still in this tab.</p>
        </header>
        <div className="rio-more-list">
          {MORE_LINKS.map((item) => (
            <Link key={item.href} href={item.href} className="rio-card rio-card-tight rio-more-row">
              <span className="rio-more-copy">
                <span className="rio-mark-label">{item.label}</span>
                <span className="rio-note">{item.blurb}</span>
              </span>
              <span className="rio-more-chevron" aria-hidden="true">
                ›
              </span>
            </Link>
          ))}
        </div>
        <Footer />
      </main>
    </div>
  );
}
