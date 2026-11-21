import Link from "next/link";

export function Footer({ onPhoto = false }: { onPhoto?: boolean }) {
  return (
    <footer className={onPhoto ? "rio-contact on-photo" : "rio-contact"}>
      <p className="rio-legal-links">
        <Link href="/privacy">Privacy</Link>
        <span aria-hidden="true"> · </span>
        <Link href="/terms">Terms</Link>
      </p>
    </footer>
  );
}

export function PhotoCredit({ children, onPhoto = false }: { children: string; onPhoto?: boolean }) {
  return <p className={onPhoto ? "rio-photo-credit on-photo" : "rio-photo-credit"}>{children}</p>;
}
