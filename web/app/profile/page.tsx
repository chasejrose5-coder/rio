import type { Metadata } from "next";
import { ProfileView } from "@/components/ProfileView";

export const metadata: Metadata = { title: "Profile · RIO" };

export default function Page() {
  return <ProfileView />;
}
