"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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

export function Nav({ active }: { active?: string }) {
  const path = usePathname();
  const router = useRouter();
  const { athlete, signOut } = useAuth();
  const [arm, setArm] = useState(false);
  const moreOpen = path === "/more" || MORE.some((item) => path === item.href) || active === "More";
  const admin = athlete?.role === "admin";
  const today = athlete?.today;
  const sessionHref = today ? `/session?date=${today}` : "/session";

  useEffect(() => {
    const key = "rio-nav-path";
    const previous = window.sessionStorage.getItem(key);
    // The underline grows once per page. A control on the same page does not replay it.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setArm(previous !== path);
    window.sessionStorage.setItem(key, path);
  }, [path]);

  return (
    <header className={arm ? "rio-nav rio-nav-arm" : "rio-nav"}>
      <div className="rio-nav-row">
        <Link className="rio-brand" href="/">
          RIO
        </Link>
        <nav className="rio-links" aria-label="Pages">
          {NAV.map((item) => {
            const on = active ? item.label === active : item.href === "/more" ? moreOpen : path === item.href;
            return (
              <Link key={item.href} href={item.href} className={on ? "is-active" : undefined} aria-current={on ? "page" : undefined}>
                {item.label}
              </Link>
            );
          })}
          {admin ? (
            <Link href="/admin" className={path === "/admin" ? "is-active" : undefined}>
              Admin
            </Link>
          ) : null}
          <Link className="rio-start-session" href={sessionHref}>
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
