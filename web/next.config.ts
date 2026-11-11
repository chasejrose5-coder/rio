import type { NextConfig } from "next";

import { apiProxyRewrites } from "./lib/deploy-proxy";

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    return apiProxyRewrites(process.env.RIO_API_ORIGIN);
  },
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [{ key: "Cache-Control", value: "private, no-store" }],
      },
    ];
  },
};

export default nextConfig;
