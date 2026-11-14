export function Footer({ onPhoto = false }: { onPhoto?: boolean }) {
  return onPhoto ? null : null;
}

export function PhotoCredit({ children, onPhoto = false }: { children: string; onPhoto?: boolean }) {
  return <p className={onPhoto ? "rio-photo-credit on-photo" : "rio-photo-credit"}>{children}</p>;
}
