"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { GUIDE_LEDE, GUIDE_SECTIONS, GUIDE_TITLE } from "@/lib/guide-copy";
import { Glossary } from "./Glossary";

function OnThisPage() {
  const [wide, setWide] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(min-width: 1024px)");
    const apply = () => setWide(query.matches);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);
  if (!wide) return null;
  return (
    <aside className="rio-on-page">
      <p className="rio-eyebrow is-quiet" id="on-this-page">
        On this page
      </p>
      <nav aria-labelledby="on-this-page">
        {GUIDE_SECTIONS.map((section) => (
          <a key={section.id} href={`#${section.id}`}>
            {section.title}
          </a>
        ))}
      </nav>
    </aside>
  );
}

export function GuideView() {
  return (
    <RequireUser title="Guide" pageClass="page-guide">
      <GuideBody />
    </RequireUser>
  );
}

function GuideBody() {
  const [current, setCurrent] = useState(GUIDE_SECTIONS[0]?.id ?? "");
  useEffect(() => {
    const nodes = GUIDE_SECTIONS.map((section) => document.getElementById(section.id)).filter(
      (node): node is HTMLElement => node instanceof HTMLElement,
    );
    if (nodes.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) setCurrent(visible.target.id);
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: [0.15, 0.4, 0.75] },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);
  return (
      <div className="page-guide rio-v3">
        <Nav />
        <main>
          <header className="rio-hero">
            <h1>{GUIDE_TITLE}</h1>
            <p className="rio-range">{GUIDE_LEDE}</p>
          </header>
          <nav className="rio-guide-contents" aria-label="Guide sections">
            {GUIDE_SECTIONS.map((section) => (
              <Link
                key={section.id}
                href={`#${section.id}`}
                aria-current={current === section.id ? "true" : undefined}
                onClick={() => setCurrent(section.id)}
              >
                {section.title}
              </Link>
            ))}
          </nav>
          <Glossary />
          <div className="rio-guide-layout">
          <div className="rio-guide-read">
          {GUIDE_SECTIONS.map((section) => (
            <section key={section.id} id={section.id} aria-labelledby={`guide-${section.id}`}>
              <h2 id={`guide-${section.id}`}>{section.title}</h2>
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
              {section.bullets ? (
                section.id === "getting-started" ? (
                  <ol>
                    {section.bullets.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ol>
                ) : (
                  <ul>
                    {section.bullets.map((item) => (
                      <li key={item} className={item.startsWith("A quality line") ? "rio-quality" : undefined}>
                        {item}
                      </li>
                    ))}
                  </ul>
                )
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
          </div>
          <OnThisPage />
          </div>
          <Footer page="guide" />
        </main>
      </div>
  );
}
