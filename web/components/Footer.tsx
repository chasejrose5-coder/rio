import Link from "next/link";
import { MEDICAL_NOTE } from "@/lib/glossary";
import type { PageMeaningId } from "@/lib/guide-copy";
import { PageMeaning } from "./PageMeaning";

export function Footer({
  onPhoto = false,
  page,
  showAbout = false,
  showMedical = true,
}: {
  onPhoto?: boolean;
  page?: PageMeaningId;
  showAbout?: boolean;
  showMedical?: boolean;
}) {
  return (
    <footer className={onPhoto ? "rio-contact on-photo" : "rio-contact"}>
      {showMedical ? <p className="rio-medical-note">{MEDICAL_NOTE}</p> : null}
      <div className="rio-legal-links">
        {page ? <PageMeaning page={page} /> : null}
        {page ? <span aria-hidden="true"> · </span> : null}
        {showAbout ? <Link href="/about">About</Link> : null}
        {showAbout ? <span aria-hidden="true"> · </span> : null}
        <Link href="/privacy">Privacy</Link>
        <span aria-hidden="true"> · </span>
        <Link href="/terms">Terms</Link>
      </div>
    </footer>
  );
}

export function PhotoCredit({ children, onPhoto = false, href }: { children: string; onPhoto?: boolean; href?: string }) {
  const klass = onPhoto ? "rio-photo-credit on-photo" : "rio-photo-credit";
  const match = href ? /^(Photo by )(.+)( on Pexels)$/.exec(children) : null;
  if (!match) return <p className={klass}>{children}</p>;
  return (
    <p className={klass}>
      {match[1]}
      <a href={href}>{match[2]}</a>
      {" on "}
      <a href="https://www.pexels.com">Pexels</a>
    </p>
  );
}
