"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

/** Admin is the RIO_ADMIN_EMAIL login. Everyone else is sent Home. */
export function useAdminOnly(): boolean {
  const { athlete, status } = useAuth();
  const router = useRouter();
  const allowed = status === "in" && athlete?.role === "admin";

  useEffect(() => {
    if (status !== "in") return;
    if (athlete?.role !== "admin") router.replace("/home");
  }, [athlete?.role, router, status]);

  return allowed;
}
