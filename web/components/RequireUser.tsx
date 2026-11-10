"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export function RequireUser({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "out") router.replace("/sign-in");
  }, [status, router]);

  if (status !== "in") {
    return <p className="rio-wait">Loading</p>;
  }
  return children;
}
