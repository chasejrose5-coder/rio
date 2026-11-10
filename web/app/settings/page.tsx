import { Suspense } from "react";
import { SettingsView } from "@/components/SettingsView";

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Loading</p>}>
      <SettingsView />
    </Suspense>
  );
}
