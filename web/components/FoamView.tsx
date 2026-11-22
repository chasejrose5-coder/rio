"use client";

import { Disclosure } from "./Disclosure";
import { FoamLibrary } from "./FoamDay";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { PageMeaning } from "./PageMeaning";
import { RequireUser } from "./RequireUser";
import { useAuth } from "@/lib/auth";
import { FOAM_DISCLAIMER } from "@/lib/foam-content";

export function FoamView() {
  return (
    <RequireUser title="Foam rolling" pageClass="page-foam">
      <FoamBody />
    </RequireUser>
  );
}

function FoamBody() {
  const { athlete } = useAuth();
  const compact = athlete?.prefs.compact === true;
  return (
    <div className={compact ? "page-foam is-compact" : "page-foam"}>
      <Nav active="Foam rolling" />
      <main>
        <header className="rio-hero">
          <h1>Foam rolling</h1>
          <p className="rio-range">A short roll after a hard day or a long run.</p>
        </header>
        <Disclosure title="Details">
          <section className="rio-foam-intro">
            <p>
              After a hard workout or a long run, roll each area for a minute. On an easy day, a rest day, or a race day it
              stays optional, at 30 seconds an area. The order rotates so the same place is not always first. Skip a spot
              that feels sharp.
            </p>
          </section>
        </Disclosure>
        <FoamLibrary />
        <p className="rio-medical">{FOAM_DISCLAIMER}</p>
        <PageMeaning page="foam" />
        <Footer />
      </main>
    </div>
  );
}
