import type { Metadata } from "next";
import { Suspense, type ReactNode } from "react";
import { OldHomeNote } from "@/components/OldHomeNote";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "RIO · Runner Intelligence Owned",
  description: "Runner Intelligence Owned",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Suspense fallback={null}>
          <OldHomeNote />
        </Suspense>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
