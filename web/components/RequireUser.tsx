"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
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

  useEffect(() => {
    if (status === "out") router.replace("/sign-in");
  }, [status, router]);

  if (status === "unreachable") {
    return <LoadingScreen label="Starting the server" onRetry={() => void refresh()} />;
  }
  // Wait until the session is known. A signed-out visit, or Back after Log out,
  // must not paint the previous runner or fire their data reads.
  if (status !== "in") {
    return <PageSkeleton title={title} variant={variant} pageClass={pageClass} pending={pendingNav} />;
  }
  return children;
}
