import Link from "next/link";
import { Footer } from "./Footer";
import { DRAFT_NOTE, LEGAL_UPDATED, type LegalPage } from "@/lib/legal-copy";
import "@/app/legal.css";

export function LegalDocument({ page }: { page: LegalPage }) {
  const other = page.path === "/privacy" ? { href: "/terms", label: "Terms" } : { href: "/privacy", label: "Privacy policy" };
  return (
    <div className="page-legal">
      <link rel="preload" href="/fonts/inter-latin-500-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      <link rel="preload" href="/fonts/inter-latin-600-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      <link rel="preload" href="/fonts/manrope-latin-800-normal.woff2" as="font" type="font/woff2" crossOrigin="anonymous" />
      <header className="rio-legal-top">
        <Link href="/">RIO</Link>
      </header>
      <main>
        <p className="rio-draft-banner" role="note">
          <strong>DRAFT</strong>
          <span>{DRAFT_NOTE}</span>
        </p>
        <h1>{page.title}</h1>
        <p className="rio-legal-updated">Sketched {LEGAL_UPDATED}. Not in effect.</p>
        <nav className="rio-legal-contents" aria-label="On this page">
          {page.sections.map((section) => (
            <a key={section.id} href={`#${section.id}`}>
              {section.title}
            </a>
          ))}
        </nav>
        {page.sections.map((section) => (
          <section key={section.id} id={section.id} aria-labelledby={`legal-${section.id}`}>
            <h2 id={`legal-${section.id}`}>{section.title}</h2>
            {section.blocks.map((block, index) =>
              block.kind === "p" ? (
                <p key={index}>{block.text}</p>
              ) : (
                <ul key={index}>
                  {block.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ),
            )}
          </section>
        ))}
        <p className="rio-legal-switch">
          <Link href={other.href}>{other.label}</Link>
        </p>
        <Footer />
      </main>
    </div>
  );
}
