import type { MetadataRoute } from "next";
import { LIVE_ORIGIN } from "@/lib/old-host";
import { PRIVATE_PREFIXES } from "@/lib/public-routes";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [...PRIVATE_PREFIXES],
    },
    sitemap: `${LIVE_ORIGIN}/sitemap.xml`,
  };
}
