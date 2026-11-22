import type { Metadata } from "next";
import { Suspense } from "react";
import { SettingsView } from "@/components/SettingsView";

export const metadata: Metadata = { title: "Settings · RIO" };

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Loading</p>}>
      <SettingsView />
    </Suspense>
  );
}
