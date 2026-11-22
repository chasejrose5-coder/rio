import type { Metadata } from "next";
import { LibraryView } from "@/components/LibraryView";

export const metadata: Metadata = { title: "Library · RIO" };

export default function Page() {
  return <LibraryView />;
}
