"use client";

import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";

export function ComingSoon({ title, note }: { title: string; note?: string }) {
  return (
    <RequireUser>
      <div className="page-plain">
        <Nav />
        <main>
          <header className="rio-hero">
            <h1>{title}</h1>
          </header>
          <p className="rio-coming">Coming in the next step.</p>
          {note ? <p className="rio-note">{note}</p> : null}
          <Footer />
        </main>
      </div>
    </RequireUser>
  );
}
