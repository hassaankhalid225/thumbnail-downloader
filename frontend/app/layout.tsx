import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/sections/Footer";
import { ANALYSIS_ENABLED, SITE_URL } from "@/lib/constants";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
});

// Metadata follows the feature flag: a title promising an AI breakdown while the
// analyser is off would put a claim in search results the page can't honour.
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: ANALYSIS_ENABLED
      ? "ThumbIQ — Download & Analyze Any Video Thumbnail (Free AI Tool)"
      : "ThumbIQ — Download Any Video Thumbnail in Every Size (Free)",
    template: "%s | ThumbIQ",
  },
  description: ANALYSIS_ENABLED
    ? "Download YouTube, TikTok, Instagram & Vimeo thumbnails in SD, HD and Full HD — then get an instant AI breakdown of colors, fonts, text placement and why the thumbnail works. Free, no signup."
    : "Download YouTube, TikTok, Instagram & Vimeo thumbnails in SD, HD, Full HD, vertical and square — as JPG, PNG or WebP, with real file sizes. Free, no signup, no watermark.",
  keywords: [
    "youtube thumbnail downloader",
    "tiktok thumbnail download",
    "instagram thumbnail downloader",
    "vimeo thumbnail downloader",
    "hd thumbnail download",
    "thumbnail grabber",
    ...(ANALYSIS_ENABLED
      ? ["thumbnail analyzer", "ai thumbnail analysis", "thumbnail color palette", "thumbnail mobile legibility"]
      : ["download thumbnail full hd", "youtube thumbnail 1080p"]),
  ],
  authors: [{ name: "ThumbIQ" }],
  openGraph: {
    title: ANALYSIS_ENABLED
      ? "ThumbIQ — Download & Analyze Any Thumbnail"
      : "ThumbIQ — Download Any Thumbnail in Every Size",
    description: ANALYSIS_ENABLED
      ? "Every size of any thumbnail, plus a measured breakdown of the colours, text placement and mobile legibility."
      : "Every size of any thumbnail, in JPG, PNG and WebP — with real file sizes, and sizes that don't exist never shown.",
    url: SITE_URL,
    siteName: "ThumbIQ",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "ThumbIQ" }],
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: ANALYSIS_ENABLED
      ? "ThumbIQ — Download & Analyze Any Thumbnail"
      : "ThumbIQ — Download Any Thumbnail in Every Size",
    description: ANALYSIS_ENABLED
      ? "Download any video thumbnail in every size, then find out exactly why it works."
      : "Download any video thumbnail in every size the platform actually stores.",
    images: ["/og-image.png"],
  },
  robots: { index: true, follow: true },
  alternates: { canonical: SITE_URL },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.png", type: "image/png", sizes: "512x512" },
    ],
    apple: "/apple-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#0A0A0D",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body>
        <a href="#main" className="skip-link">
          Skip to the tool
        </a>
        <Navbar />
        <main id="main">{children}</main>
        <Footer />
        <script
          type="application/ld+json"
          // Structured data for the app itself. The FAQ and HowTo blocks live on the
          // pages that actually contain those sections.
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "ThumbIQ",
              url: SITE_URL,
              applicationCategory: "MultimediaApplication",
              operatingSystem: "Any",
              description: ANALYSIS_ENABLED
                ? "Download any video thumbnail in every size and get a measured analysis of its colours, text placement, mobile legibility and composition."
                : "Download any video thumbnail in every size the platform actually stores, as JPG, PNG or WebP, with real file sizes.",
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                "Thumbnail download in 8 sizes and 3 formats",
                "Verified sizes — non-existent renditions are never listed",
                "Honest upscale labelling",
                "Vertical and square crops anchored on the subject",
                "Bulk ZIP download",
                ...(ANALYSIS_ENABLED
                  ? [
                      "Colour palette extraction with harmony detection",
                      "Mobile legibility simulation at real render sizes",
                      "YouTube UI safe-zone collision detection",
                      "AI verdict grounded in measured metrics",
                    ]
                  : []),
              ],
            }),
          }}
        />
      </body>
    </html>
  );
}
