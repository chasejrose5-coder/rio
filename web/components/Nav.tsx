"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/home", label: "Home" },
  { href: "/plan", label: "Plan" },
  { href: "/activity", label: "Activity" },
  { href: "/library", label: "Library" },
  { href: "/more", label: "More" },
];

const MORE = [
  { href: "/past-seasons", label: "Past seasons" },
  { href: "/profile", label: "Profile" },
  { href: "/settings", label: "Settings" },
  { href: "/about", label: "About" },
  { href: "/creators", label: "Creators" },
];

export function Nav() {
  const path = usePathname();
  const router = useRouter();
  const { athlete, signOut } = useAuth();
  const moreOpen = path === "/more" || MORE.some((item) => path === item.href);
  const admin = athlete?.role === "admin";

  return (
    <header className="rio-nav">
      <div className="rio-nav-row">
        <Link className="rio-brand" href="/">
          RIO
        </Link>
        <nav className="rio-links" aria-label="Pages">
          {NAV.map((item) => {
            const active = item.href === "/more" ? moreOpen : path === item.href;
            return (
              <Link key={item.href} href={item.href} className={active ? "is-active" : undefined} aria-current={active ? "page" : undefined}>
                {item.label}
              </Link>
            );
          })}
          {admin ? (
            <Link href="/admin" className={path === "/admin" ? "is-active" : undefined}>
              Admin
            </Link>
          ) : null}
          <Link className="rio-start-session" href="/session">
            Start session
          </Link>
          <button
            type="button"
            className="rio-logout"
            onClick={() => {
              void signOut().then(() => router.replace("/sign-in"));
            }}
          >
            Log out
          </button>
        </nav>
      </div>
      {moreOpen ? (
        <nav className="rio-subnav" aria-label="More">
          {MORE.map((item) => (
            <Link key={item.href} href={item.href} className={path === item.href ? "is-active" : undefined}>
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </header>
  );
}
