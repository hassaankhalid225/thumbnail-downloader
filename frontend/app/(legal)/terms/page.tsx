import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";

export const metadata: Metadata = {
  title: "Terms",
  description:
    "ThumbIQ is an analysis and research tool. Thumbnails belong to their creators. Scores are measurements, not performance predictions.",
};

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of use"
      updated="27 July 2026"
      intro="ThumbIQ is an analysis, research and educational reference tool. Using it means agreeing to the following, which is short because the service is narrow."
      sections={[
        {
          heading: "What ThumbIQ is for",
          paragraphs: [
            "Studying thumbnails: reading a palette, checking a text placement, measuring whether your own draft survives at phone size, understanding why a competitor's design works.",
            "The value the service adds is the measurement, not the image. That distinction is the whole basis on which it operates.",
          ],
        },
        {
          heading: "What it is not for",
          bullets: [
            "Republishing someone else's thumbnail as your own. Thumbnails are copyrighted works owned by the creators who made them.",
            "Building a redistribution service, an archive, or a public gallery of other people's images.",
            "Bypassing any platform's access controls. ThumbIQ reads publicly served content only, and never authenticates on your behalf or accepts credentials for any platform.",
            "Automated bulk extraction. Rate limits apply per IP and are enforced.",
          ],
        },
        {
          heading: "About the scores",
          paragraphs: [
            "Every number ThumbIQ shows is a measurement of real pixels or a documented heuristic applied to one. The formulas and weights are published in full and exposed in the interface.",
            "They are not predictions. ThumbIQ makes no claim that acting on its advice will change your click-through rate, your view count, or any other platform metric, and it will not produce a forecast if you ask it to.",
          ],
        },
        {
          heading: "About the honest labels",
          bullets: [
            "A size marked upscaled is upscaled — the pixels are interpolated, not recovered.",
            "The font read is a classification of letterform geometry with closest free-font suggestions. It is never an identification, and it says so everywhere it appears.",
            "Expression detection is a geometric estimate, not a trained classifier, and is labelled as an estimate.",
            "A score shown as a dash could not be measured. It is excluded from the overall rather than filled in with a placeholder.",
          ],
        },
        {
          heading: "Availability",
          paragraphs: [
            "The service is provided as-is, with no uptime guarantee. Upstream platforms change their markup and rate limits without notice; when a link cannot be resolved you get a clear message rather than a broken result.",
            "The AI verdict is rate-limited per IP because it costs real money to run. When that limit is reached, or the AI provider is unavailable, every deterministic measurement still runs and the interface says what happened.",
          ],
        },
        {
          heading: "Liability",
          paragraphs: [
            "To the maximum extent permitted by law, ThumbIQ is not liable for any loss arising from use of the service, including decisions made on the basis of its output.",
            "You are responsible for how you use any image you download, and for complying with the terms of the platform it came from.",
          ],
        },
        {
          heading: "Contact",
          paragraphs: ["legal@thumbiq.app. Takedown requests go to dmca@thumbiq.app — see the DMCA page."],
        },
      ]}
    />
  );
}
