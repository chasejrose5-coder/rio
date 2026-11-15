"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LoadingScreen } from "./LoadingScreen";
import { useAuth } from "@/lib/auth";

export function RequireUser({ children }: { children: React.ReactNode }) {
  const { status, refresh } = useAuth();
  const router = useRouter();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    // The server render stays the shell. The page mounts on the client so its
    // read starts beside /auth/me, and useSearchParams is not prerendered.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShown(true);
  }, []);

  useEffect(() => {
    if (status === "out") router.replace("/sign-in");
  }, [status, router]);

  if (!shown || status === "out") {
    return <LoadingScreen />;
  }
  if (status === "unreachable") {
    return <LoadingScreen label="Starting the server" onRetry={() => void refresh()} />;
  }
  return children;
}
