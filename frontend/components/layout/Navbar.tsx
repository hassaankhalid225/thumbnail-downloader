import Link from "next/link";

import { ANALYSIS_ENABLED } from "@/lib/constants";

// Compare and Channel are analyser features. With the analyser off they are closed, so
// they don't appear here — a nav link to a switched-off feature is a dead end.
const LINKS = [
  ...(ANALYSIS_ENABLED
    ? [
        { href: "/compare", label: "Compare" },
        { href: "/channel", label: "Channel report" },
      ]
    : []),
  { href: "/youtube-thumbnail-downloader", label: "YouTube" },
  { href: "/tiktok-thumbnail-downloader", label: "TikTok" },
  { href: "/#faq", label: "FAQ" },
];

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-[#232330]/70 bg-[#0A0A0D]/80 backdrop-blur-xl">
      <nav
        aria-label="Main"
        className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8"
      >
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-[#C8FF3D]/30 bg-[#C8FF3D]/10">
            {/* A reticle, not a play button — this tool measures, it doesn't play. */}
            <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
              <circle cx="12" cy="12" r="7" stroke="#C8FF3D" strokeWidth="1.6" fill="none" />
              <circle cx="12" cy="12" r="2" fill="#C8FF3D" />
              <path d="M12 1v4M12 19v4M1 12h4M19 12h4" stroke="#C8FF3D" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </span>
          <span className="text-[17px] font-extrabold tracking-tight">
            Thumb<span className="text-[#C8FF3D]">IQ</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-[#8E8EA8] transition-colors hover:bg-[#16161D] hover:text-[#F2F2F7] sm:block"
            >
              {link.label}
            </Link>
          ))}
          <Link
            href="/#tool"
            className="ml-2 rounded-lg bg-[#C8FF3D] px-4 py-2 text-sm font-bold text-black transition-all hover:brightness-110"
          >
            {ANALYSIS_ENABLED ? "Analyze" : "Download"}
          </Link>
        </div>
      </nav>
    </header>
  );
}
