import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/constants";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Share links are per-user payloads, not content. Indexing them would fill search
      // results with thousands of near-identical score pages.
      disallow: ["/api/", "/analyze/"],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
