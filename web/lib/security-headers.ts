/** Response headers for HTML and static files.

The policy is enforced. Google sign-in needs the Identity Services script,
its button stylesheet, and the font file that stylesheet requests. Those
hosts are listed so the button still renders. Violations POST to
`/csp-report` and the body is discarded.

`frame-ancestors` is in the same policy, with `X-Frame-Options` for older
browsers.

`Access-Control-Allow-Origin: *` is not set in this repo. FastAPI allows
one configured origin. Vercel's CDN adds `*` on prerendered HTML and on
files in `public/`. These headers replace that on every path except
`/api`, so the proxied API keeps its own allowlist.
*/

export const SITE_ORIGIN = "https://www.riorunning.com";

export const CSP_REPORT_PATH = "/csp-report";

function contentSecurityPolicy(dev: boolean): string {
  const script = ["'self'", "'unsafe-inline'", "https://vercel.live", "https://accounts.google.com"];
  const connect = ["'self'", "https://rio-api.onrender.com", "https://vercel.live", "https://accounts.google.com"];
  // Next dev rebuilds with eval, and Playwright talks to the API on port 8000.
  if (dev) {
    script.push("'unsafe-eval'");
    connect.push("http://localhost:8000", "http://127.0.0.1:8000");
  }
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    `script-src ${script.join(" ")}`,
    "style-src 'self' 'unsafe-inline' https://accounts.google.com",
    "img-src 'self' data: blob:",
    "font-src 'self' https://fonts.gstatic.com",
    `connect-src ${connect.join(" ")}`,
    "frame-src https://vercel.live https://accounts.google.com",
    "form-action 'self'",
    `report-uri ${CSP_REPORT_PATH}`,
    "report-to csp",
  ].join("; ");
}

const CONTENT_SECURITY_POLICY = contentSecurityPolicy(false);

export const DOCUMENT_SECURITY_HEADERS: { key: string; value: string }[] = [
  { key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY },
  { key: "Reporting-Endpoints", value: `csp="${CSP_REPORT_PATH}"` },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Access-Control-Allow-Origin", value: SITE_ORIGIN },
];

/** Pages and public files. `/api` is the FastAPI proxy and is left alone.

Development adds eval and the local API port. Production does not.
*/
export function documentSecurityRoutes(
  dev = process.env.NODE_ENV !== "production",
): { source: string; headers: { key: string; value: string }[] }[] {
  const headers = dev
    ? DOCUMENT_SECURITY_HEADERS.map((item) =>
        item.key === "Content-Security-Policy" ? { key: item.key, value: contentSecurityPolicy(true) } : item,
      )
    : DOCUMENT_SECURITY_HEADERS;
  return [
    { source: "/", headers },
    { source: "/:path((?!api$).*)", headers },
  ];
}
