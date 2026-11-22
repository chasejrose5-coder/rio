"use client";

import { Disclosure } from "./Disclosure";
import { Footer } from "./Footer";
import { CoreLibrary } from "./CoreDay";
import { Nav } from "./Nav";
import { PageMeaning } from "./PageMeaning";
import { RequireUser } from "./RequireUser";
import { useAuth } from "@/lib/auth";
import { CORE_DISCLAIMER } from "@/lib/core-content";

export function CoreView() {
  return (
    <RequireUser title="Core" pageClass="page-core">
      <CoreBody />
    </RequireUser>
  );
}

function CoreBody() {
  const { athlete } = useAuth();
  const compact = athlete?.prefs.compact === true;
  return (
    <div className={compact ? "page-core is-compact" : "page-core"}>
      <Nav active="Core" />
      <main>
        <header className="rio-hero">
          <h1>Core</h1>
          <p className="rio-range">Today’s circuit is on the workout. A hard day stays near 8 minutes.</p>
        </header>
        <Disclosure title="Details">
          <section className="rio-core-intro">
            <p>
              An easy day takes 12 to 15. The week rotates anti-extension, anti-rotation, lateral work, flexion, and
              running-specific moves.
            </p>
          </section>
        </Disclosure>
        <CoreLibrary />
        <p className="rio-medical">{CORE_DISCLAIMER}</p>
        <PageMeaning page="core" />
        <Footer />
      </main>
    </div>
  );
}
