import { Suspense } from "react";
import { StravaSettings } from "@/components/StravaSettings";

export default function Page() {
  return (
    <Suspense fallback={<p className="rio-wait">Loading</p>}>
      <StravaSettings />
    </Suspense>
  );
}
