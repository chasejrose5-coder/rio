"use client";

import { useRouter } from "next/navigation";
import { previewing, stopPreview } from "@/lib/api";

export function PreviewBanner({ banner }: { banner?: string }) {
  const router = useRouter();
  if (!previewing() && !banner) return null;
  return (
    <div className="rio-preview">
      <p className="rio-note">{banner || "Test athlete preview. Read only: nothing here is saved."}</p>
      <button
        type="button"
        className="rio-secondary"
        onClick={() => {
          stopPreview();
          router.push("/admin");
        }}
      >
        Back to admin
      </button>
    </div>
  );
}
