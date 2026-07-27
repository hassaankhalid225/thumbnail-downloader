import type { Metadata } from "next";

import { SITE_URL } from "@/lib/constants";

// The page itself is a client component and can't export metadata, so it lives here.
export const metadata: Metadata = {
  title: "Compare Thumbnails Side by Side — 2 to 4 at Once",
  description:
    "Put two to four video thumbnails head to head. The same eight measurements each — stopping power, mobile legibility, contrast, composition — with a winner per category. Free, no signup.",
  alternates: { canonical: `${SITE_URL}/compare` },
  openGraph: {
    title: "Compare thumbnails side by side | ThumbIQ",
    description:
      "Two to four thumbnails, the same eight measurements each, and a winner per category.",
    url: `${SITE_URL}/compare`,
  },
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return children;
}
