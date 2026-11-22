import Link from "next/link";
import { MEDICAL_NOTE } from "@/lib/glossary";

export function Footer({ onPhoto = false }: { onPhoto?: boolean }) {
  return (
    <footer className={onPhoto ? "rio-contact on-photo" : "rio-contact"}>
      <p className="rio-medical-note">{MEDICAL_NOTE}</p>
      <p className="rio-legal-links">
        <Link href="/privacy">Privacy</Link>
        <span aria-hidden="true"> · </span>
        <Link href="/terms">Terms</Link>
      </p>
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
