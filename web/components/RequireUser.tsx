"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LoadingScreen } from "./LoadingScreen";
import { PageSkeleton } from "./PageSkeleton";
import { useAuth } from "@/lib/auth";

export function RequireUser({
  children,
  title,
  variant = "cards",
  pageClass,
  pendingNav = false,
}: {
  children: React.ReactNode;
  title?: string;
  variant?: "home" | "cards" | "calendar";
  pageClass?: string;
  pendingNav?: boolean;
}) {
  const { status, refresh } = useAuth();
  const router = useRouter();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    // The server render stays the skeleton. After mount, the page read starts
    // beside /auth/me, and useSearchParams is not prerendered.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShown(true);
  }, []);

  useEffect(() => {
    if (status === "out") router.replace("/sign-in");
  }, [status, router]);

  if (status === "unreachable") {
    return <LoadingScreen label="Starting the server" onRetry={() => void refresh()} />;
  }
  if (status === "in") return children;
  if (!shown || status === "out") {
    return <PageSkeleton title={title} variant={variant} pageClass={pageClass} pending={pendingNav} />;
  }
  return children;
}
