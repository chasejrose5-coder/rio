const CONTACT = "chasejrose5@gmail.com";

export function Footer({ onPhoto = false }: { onPhoto?: boolean }) {
  return (
    <p className={onPhoto ? "rio-contact on-photo" : "rio-contact"}>
      Questions or feedback? Email <a href={`mailto:${CONTACT}`}>{CONTACT}</a>
    </p>
  );
}

export function PhotoCredit({ children, onPhoto = false }: { children: string; onPhoto?: boolean }) {
  return <p className={onPhoto ? "rio-photo-credit on-photo" : "rio-photo-credit"}>{children}</p>;
}
