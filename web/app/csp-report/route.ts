/** Browser CSP reports. The body is discarded so a report cannot land in logs. */

export function POST(): Response {
  return new Response(null, {
    status: 204,
    headers: { "Cache-Control": "no-store" },
  });
}
