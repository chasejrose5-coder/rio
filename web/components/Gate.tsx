"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { landingPath } from "@/lib/landing";

export function Gate() {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "out") {
      router.replace("/sign-in");
      return;
    }
    if (status !== "in") return;
    let live = true;
    void api.currentSeason().then((season) => {
      if (live) router.replace(landingPath(season));
    });
    return () => {
      live = false;
    };
  }, [status, router]);

  return <p className="rio-wait">Loading</p>;
}
