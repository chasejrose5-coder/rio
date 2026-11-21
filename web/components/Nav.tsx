"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { WakeHint } from "./LoadingScreen";
import { api, stopPreview } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { forgetLanding, landingPath, rememberedLanding, rememberLanding } from "@/lib/landing";
import { navShouldArm } from "@/lib/motion";
import { sessionHref } from "@/lib/session";

const NAV = [
  { href: "/home", label: "Home" },
  { href: "/plan", label: "Plan" },
  { href: "/stretch", label: "Training" },
  { href: "/activity", label: "Activity" },
  { href: "/more", label: "More" },
];

const TRAINING = [
  { href: "/library", label: "Library" },
  { href: "/stretch", label: "Stretching" },
  { href: "/recovery", label: "Recovery" },
  { href: "/core", label: "Core" },
  { href: "/foam", label: "Foam rolling" },
];

const MORE = [
  { href: "/past-seasons", label: "Past seasons" },
  { href: "/profile", label: "Profile" },
  { href: "/settings", label: "Settings" },
  { href: "/guide", label: "Guide" },
  { href: "/about", label: "About" },
  { href: "/creators", label: "Creators" },
];

export function Nav({ active }: { active?: string }) {
  const path = usePathname();
  const router = useRouter();
  const { status, athlete, signOut } = useAuth();
  const [arm, setArm] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [brand, setBrand] = useState("/");
  const trainingOpen =
    path === "/library" ||
    path === "/stretch" ||
    path === "/recovery" ||
    path === "/core" ||
    path === "/foam" ||
    path === "/training" ||
    active === "Training" ||
    active === "Library" ||
    active === "Stretching" ||
    active === "Recovery" ||
    active === "Core" ||
    active === "Foam rolling";
  const moreOpen = path === "/more" || MORE.some((item) => path === item.href) || active === "More";
  const admin = athlete?.role === "admin";
  const startSession = sessionHref(athlete?.next_session);

  useEffect(() => {
    const key = "rio-nav-path";
    const previous = window.sessionStorage.getItem(key);
    // The underline grows once per page. A control on the same page does not replay it.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setArm(navShouldArm(previous, path));
    window.sessionStorage.setItem(key, path);
    setMenuOpen(false);
  }, [path]);

  useEffect(() => {
    if (status !== "in") return;
    const cached = rememberedLanding();
    if (cached) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBrand(cached);
    }
    let live = true;
    void api
      .currentSeason()
      .then((season) => {
        if (!live) return;
        const next = landingPath(season);
        rememberLanding(next);
        setBrand(next);
      })
      .catch(() => {
        if (!live) return;
        rememberLanding("/start");
        setBrand("/start");
      });
    return () => {
      live = false;
    };
  }, [status]);

  if (status !== "in") {
    return (
      <header className="rio-nav rio-nav-signed-out">
        <div className="rio-nav-row">
          <Link className="rio-brand" href="/">
            RIO
          </Link>
          {status === "loading" ? null : (
            <Link className="rio-signed-out-login" href="/sign-in">
              Log in
            </Link>
          )}
        </div>
      </header>
    );
  }

  return (
    <header className={arm ? "rio-nav rio-nav-arm" : "rio-nav"}>
      <WakeHint />
      <div className="rio-nav-row">
        <Link
          className="rio-brand"
          href={status === "in" ? brand : "/"}
          onClick={(event) => {
            if (status !== "in") return;
            const target = rememberedLanding() || (brand === "/home" || brand === "/start" ? brand : null);
            if (!target) return;
            event.preventDefault();
            router.push(target);
          }}
        >
          RIO
        </Link>
        <nav className="rio-links" aria-label="Pages">
          {NAV.map((item) => {
            const on =
              item.label === "Training"
                ? trainingOpen
                : item.label === "More"
                  ? moreOpen
                  : active
                    ? item.label === active
                    : path === item.href;
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
          <div className={menuOpen ? "rio-overflow is-open" : "rio-overflow"}>
            <button
              type="button"
              className="rio-overflow-toggle"
              aria-expanded={menuOpen}
              aria-controls="rio-account-menu"
              onClick={() => setMenuOpen((open) => !open)}
            >
              Menu
            </button>
            <div className="rio-overflow-panel" id="rio-account-menu">
              <Link className="rio-start-session" href={startSession}>
                Start session
              </Link>
              <button
                type="button"
                className="rio-logout"
                onClick={() => {
                  stopPreview();
                  forgetLanding();
                  void signOut().then(() => router.replace("/sign-in"));
                }}
              >
                Log out
              </button>
            </div>
          </div>
        </nav>
      </div>
      {trainingOpen ? (
        <nav className="rio-subnav" aria-label="Training">
          {TRAINING.map((item) => {
            const on = path === item.href || active === item.label;
            return (
              <Link key={item.href} href={item.href} className={on ? "is-active" : undefined} aria-current={on ? "page" : undefined}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      ) : null}
      {moreOpen ? (
        <nav className="rio-subnav" aria-label="More">
          {MORE.map((item) => {
            const on = path === item.href;
            return (
              <Link key={item.href} href={item.href} className={on ? "is-active" : undefined} aria-current={on ? "page" : undefined}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      ) : null}
    </header>
  );
}
