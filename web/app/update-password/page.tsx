import type { Metadata } from "next";
import ResetPasswordPage from "@/components/ResetPasswordPage";

export const metadata: Metadata = { title: "Update password · RIO" };

export default function Page() {
  return <ResetPasswordPage />;
}
