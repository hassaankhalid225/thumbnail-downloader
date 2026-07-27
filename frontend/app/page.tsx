import { GridBackground } from "@/components/hero";
import { FAQ, FAQ_ITEMS, Features, HowItWorks, SupportedPlatforms, UseCases } from "@/components/sections";
import { ThumbIQTool } from "@/components/ThumbIQTool";
import { ANALYSIS_ENABLED, SITE_URL } from "@/lib/constants";

/**
 * A server component. Only <ThumbIQTool /> is a client island — the hero copy, the
 * feature grid, the platform list, the use cases and the FAQ are all rendered on the
 * server and ship no JavaScript.
 */
export default function HomePage() {
  return (
    <>
      <div className="relative">
        <GridBackground />

        <section className="relative mx-auto max-w-5xl px-5 pb-16 pt-16 sm:px-8 sm:pt-24">
          {/* The copy tracks what the product actually does. With the analyser off,
              promising an AI breakdown would be a claim the page can't cash. */}
          <div className="text-center">
            <p className="eyebrow">
              {ANALYSIS_ENABLED ? "Thumbnail downloader + analyzer" : "Thumbnail downloader"}
            </p>
            <h1 className="mt-4 text-[38px] font-extrabold leading-[1.05] tracking-tight sm:text-[54px] lg:text-[68px]">
              {ANALYSIS_ENABLED ? (
                <>
                  <span className="block">Steal the thumbnail.</span>
                  <span className="block bg-gradient-to-r from-[#C8FF3D] to-[#22D3EE] bg-clip-text text-transparent">
                    Understand the strategy.
                  </span>
                </>
              ) : (
                <>
                  <span className="block">Any thumbnail.</span>
                  <span className="block bg-gradient-to-r from-[#C8FF3D] to-[#22D3EE] bg-clip-text text-transparent">
                    Every size that exists.
                  </span>
                </>
              )}
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-[15px] leading-relaxed text-[#8E8EA8] sm:text-[17px]">
              {ANALYSIS_ENABLED
                ? "Download any thumbnail in every size — then let AI break down the colours, fonts, text placement and why it actually works."
                : "Paste a link from YouTube, TikTok, Instagram, Vimeo or 1,800 other sites. Eight sizes, three formats, real file sizes — and sizes that don't exist are never shown."}
            </p>
          </div>

          <div className="mt-9">
            <ThumbIQTool />
          </div>
        </section>

        <HowItWorks />
        <Features />
        <SupportedPlatforms />
        <UseCases />
        <FAQ />
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            {
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: FAQ_ITEMS.map((item) => ({
                "@type": "Question",
                name: item.q,
                acceptedAnswer: { "@type": "Answer", text: item.a },
              })),
            },
            {
              "@context": "https://schema.org",
              "@type": "HowTo",
              name: ANALYSIS_ENABLED
                ? "How to download and analyze a video thumbnail"
                : "How to download a video thumbnail in every size",
              totalTime: ANALYSIS_ENABLED ? "PT15S" : "PT5S",
              step: [
                {
                  "@type": "HowToStep",
                  name: "Paste a link",
                  text: ANALYSIS_ENABLED
                    ? "Paste any video or post URL into the input, or drop your own image onto the page."
                    : "Paste any video or post URL into the input.",
                  url: `${SITE_URL}/#tool`,
                },
                {
                  "@type": "HowToStep",
                  name: "Pick a size",
                  text: "Choose from eight sizes in JPG, PNG or WebP. Upscaled sizes are labelled as upscaled, and sizes that don't exist are never shown.",
                  url: `${SITE_URL}/#tool`,
                },
                ...(ANALYSIS_ENABLED
                  ? [
                      {
                        "@type": "HowToStep",
                        name: "Read the analysis",
                        text: "Review the eight measured sub-scores, the palette, the text placement and the mobile legibility check.",
                        url: `${SITE_URL}/#tool`,
                      },
                    ]
                  : [
                      {
                        "@type": "HowToStep",
                        name: "Download",
                        text: "Download a single size, or select several and take them as a ZIP.",
                        url: `${SITE_URL}/#tool`,
                      },
                    ]),
              ],
            },
          ]),
        }}
      />
    </>
  );
}
