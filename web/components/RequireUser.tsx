"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LoadingScreen } from "./LoadingScreen";
import { useAuth } from "@/lib/auth";

export function RequireUser({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "out") router.replace("/sign-in");
  }, [status, router]);

  if (status !== "in") {
    return <LoadingScreen />;
  }
  return children;
}
