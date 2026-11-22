import type { Metadata } from "next";
import { ConfirmScreen } from "@/components/AuthScreen";

export const metadata: Metadata = { title: "Confirm email · RIO" };

export default function Page() {
  return <ConfirmScreen />;
}
