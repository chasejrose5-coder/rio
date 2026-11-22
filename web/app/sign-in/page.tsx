import type { Metadata } from "next";
import { SignInScreen } from "@/components/AuthScreen";

export const metadata: Metadata = { title: "Log in · RIO" };

export default function Page() {
  return <SignInScreen />;
}
