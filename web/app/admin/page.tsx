import type { Metadata } from "next";
import { AdminView } from "@/components/AdminView";

export const metadata: Metadata = { title: "Admin · RIO" };

export default function Page() {
  return <AdminView />;
}
