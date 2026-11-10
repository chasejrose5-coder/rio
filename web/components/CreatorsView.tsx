"use client";

import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { CREATORS } from "@/lib/creators";
import { useAuth } from "@/lib/auth";

const PHOTO = "/photos/chase-blocks.jpg";

export function CreatorsView() {
  return (
    <RequireUser>
      <CreatorsBody />
    </RequireUser>
  );
}

function CreatorsBody() {
  const { athlete } = useAuth();
  const [arm, setArm] = useState(false);
  const [rise, setRise] = useState(false);
  const compact = athlete?.prefs.compact === true;

  useEffect(() => {
    const key = "rio-motion-page";
    const first = window.sessionStorage.getItem(key) !== "creators";
    window.sessionStorage.setItem(key, "creators");
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
    <div className={compact ? "page-creators is-compact" : "page-creators"}>
      <Nav />
      <main className={rise ? "rio-stagger" : undefined}>
        <header className="rio-hero rio-creator-hero">
          <p className="rio-synthetic">{CREATORS.banner}</p>
          <h1>{CREATORS.heading}</h1>
        </header>
        <div className="rio-creator-layout">
          <figure className="rio-creator-photo">
            <picture>
              <source
                srcSet="/photos/chase-blocks-800.webp 800w, /photos/chase-blocks-1200.webp 1200w"
                sizes="(max-width: 1200px) 100vw, 1200px"
                type="image/webp"
              />
              <source
                srcSet={`/photos/chase-blocks-800.jpg 800w, ${PHOTO} 1600w`}
                sizes="(max-width: 1200px) 100vw, 1200px"
              />
              <img src={PHOTO} width={1600} height={900} alt={CREATORS.alt} />
            </picture>
          </figure>
          <article className="rio-creator">
            <h2 className="rio-creator-name">{CREATORS.name}</h2>
            {CREATORS.paragraphs.map((paragraph) => (
              <p key={paragraph} className="rio-creator-bio">
                {paragraph}
              </p>
            ))}
            <p className="rio-creator-close">{CREATORS.close}</p>
          </article>
        </div>
        <div hidden dangerouslySetInnerHTML={{ __html: CREATORS.comment }} />
        <Footer />
      </main>
    </div>
  );
}
