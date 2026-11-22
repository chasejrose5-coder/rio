import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Page not found · RIO" };

export default function NotFound() {
  return (
    <div className="page-missing">
      <main>
        <p className="rio-missing-mark">RIO</p>
        <h1>Page not found</h1>
        <p>That address is not a page in RIO.</p>
        <Link className="rio-primary rio-missing-home" href="/">
          Back home
        </Link>
      </main>
    </div>
  );
}
