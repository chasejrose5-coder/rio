"use client";

import Link from "next/link";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { PageMeaning } from "./PageMeaning";
import { RequireUser } from "./RequireUser";
import { GUIDE_LEDE, GUIDE_SECTIONS, GUIDE_TITLE } from "@/lib/guide-copy";

export function GuideView() {
  return (
    <RequireUser>
      <div className="page-guide">
        <Nav />
        <main>
          <header className="rio-hero">
            <h1>{GUIDE_TITLE}</h1>
            <p className="rio-range">{GUIDE_LEDE}</p>
          </header>
          <nav className="rio-guide-contents" aria-label="Guide sections">
            {GUIDE_SECTIONS.map((section) => (
              <Link key={section.id} href={`#${section.id}`}>
                {section.title}
              </Link>
            ))}
          </nav>
          {GUIDE_SECTIONS.map((section) => (
            <section key={section.id} id={section.id} aria-labelledby={`guide-${section.id}`}>
              <h2 id={`guide-${section.id}`}>{section.title}</h2>
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              {section.bullets ? (
                <ul>
                  {section.bullets.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
              {section.details?.map((detail) => (
                <details key={detail.summary}>
                  <summary>{detail.summary}</summary>
                  {detail.paragraphs.map((paragraph) => (
                    <p key={paragraph}>{paragraph}</p>
                  ))}
                </details>
              ))}
            </section>
          ))}
          <PageMeaning page="guide" />
          <Footer />
        </main>
      </div>
    </RequireUser>
  );
}
