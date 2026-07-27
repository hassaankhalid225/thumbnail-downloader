import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { GridBackground } from "@/components/hero";
import { ThumbIQTool } from "@/components/ThumbIQTool";
import { ANALYSIS_ENABLED, SITE_URL } from "@/lib/constants";
import { PLATFORM_PAGES, getPlatformPage, resolvePlatformPage } from "@/lib/platformPages";

export function generateStaticParams() {
  return PLATFORM_PAGES.map((page) => ({ slug: page.slug }));
}

// Only the six real platform slugs exist here. Without this, every unmatched
// single-segment path would render this route at request time just to 404.
export const dynamicParams = false;

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const raw = getPlatformPage(slug);
  if (!raw) return {};
  const page = resolvePlatformPage(raw, ANALYSIS_ENABLED);

  return {
    // No " | ThumbIQ" here — the root layout's title template already appends it, and
    // spelling it out again produced "… | ThumbIQ | ThumbIQ" in the browser tab.
    title: page.title,
    description: page.description,
    alternates: { canonical: `${SITE_URL}/${page.slug}` },
    openGraph: {
      title: page.title,
      description: page.description,
      url: `${SITE_URL}/${page.slug}`,
      type: "website",
    },
  };
}

export default async function PlatformPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const raw = getPlatformPage(slug);
  if (!raw) notFound();
  const page = resolvePlatformPage(raw, ANALYSIS_ENABLED);

  return (
    <>
      <div className="relative">
        <GridBackground />

        <section className="relative mx-auto max-w-5xl px-5 pb-14 pt-14 sm:px-8 sm:pt-20">
          <nav aria-label="Breadcrumb" className="eyebrow">
            <Link href="/" className="hover:text-[#C8FF3D]">
              ThumbIQ
            </Link>
            <span className="mx-2">/</span>
            <span>{page.name}</span>
          </nav>

          <h1 className="mt-4 text-[34px] font-extrabold leading-[1.08] tracking-tight sm:text-[46px]">
            {page.h1}
          </h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-[#8E8EA8] sm:text-[17px]">
            {page.intro}
          </p>

          <div className="mt-9">
            <ThumbIQTool />
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-5 py-16 sm:px-8">
          <p className="eyebrow">Sizes available</p>
          <h2 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">
            What you get from a {page.name} link
          </h2>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-[#232330]">
                  <th scope="col" className="py-2.5 pr-4 text-left text-[12px] font-bold text-[#8E8EA8]">
                    Size
                  </th>
                  <th scope="col" className="py-2.5 pr-4 text-left text-[12px] font-bold text-[#8E8EA8]">
                    Dimensions
                  </th>
                  <th scope="col" className="py-2.5 text-left text-[12px] font-bold text-[#8E8EA8]">
                    Notes
                  </th>
                </tr>
              </thead>
              <tbody>
                {page.sizes.map((size) => (
                  <tr key={size.label} className="border-b border-[#232330] last:border-0">
                    <td className="py-3 pr-4 font-semibold text-[#F2F2F7]">{size.label}</td>
                    <td className="mono py-3 pr-4 text-[#C8FF3D]">{size.dimensions}</td>
                    <td className="py-3 text-[13px] text-[#8E8EA8]">{size.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-14 space-y-10">
            {page.sections.map((section) => (
              <article key={section.heading}>
                <h2 className="text-xl font-bold tracking-tight text-[#F2F2F7] sm:text-2xl">
                  {section.heading}
                </h2>
                {section.body.map((paragraph, index) => (
                  <p
                    key={index}
                    className="mt-3 text-[15px] leading-relaxed text-[#8E8EA8]"
                  >
                    {paragraph}
                  </p>
                ))}
              </article>
            ))}
          </div>

          <div className="mt-16">
            <p className="eyebrow">{page.name} questions</p>
            <h2 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">
              Common questions
            </h2>
            <div className="mt-6 space-y-3">
              {page.faqs.map((faq) => (
                <details
                  key={faq.q}
                  className="panel group p-5 [&_summary::-webkit-details-marker]:hidden"
                >
                  <summary className="flex cursor-pointer items-start justify-between gap-4 text-[15px] font-bold text-[#F2F2F7]">
                    {faq.q}
                    <span className="mt-0.5 shrink-0 text-[#C8FF3D] transition-transform group-open:rotate-45">
                      +
                    </span>
                  </summary>
                  <p className="mt-3 text-sm leading-relaxed text-[#8E8EA8]">{faq.a}</p>
                </details>
              ))}
            </div>
          </div>

          <div className="mt-14 rounded-2xl border border-[#232330] bg-[#101015] p-6">
            <p className="text-sm font-bold text-[#F2F2F7]">Other platforms</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {PLATFORM_PAGES.filter((other) => other.slug !== page.slug).map((other) => (
                <Link
                  key={other.slug}
                  href={`/${other.slug}`}
                  className="rounded-lg border border-[#232330] bg-[#16161D] px-3 py-2 text-[13px] font-medium text-[#8E8EA8] transition-colors hover:border-[#33334A] hover:text-[#F2F2F7]"
                >
                  {other.name}
                </Link>
              ))}
            </div>
          </div>
        </section>
      </div>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            {
              "@context": "https://schema.org",
              "@type": "BreadcrumbList",
              itemListElement: [
                { "@type": "ListItem", position: 1, name: "ThumbIQ", item: SITE_URL },
                {
                  "@type": "ListItem",
                  position: 2,
                  name: page.name,
                  item: `${SITE_URL}/${page.slug}`,
                },
              ],
            },
            {
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: page.faqs.map((faq) => ({
                "@type": "Question",
                name: faq.q,
                acceptedAnswer: { "@type": "Answer", text: faq.a },
              })),
            },
          ]),
        }}
      />
    </>
  );
}
