import type { Metadata } from "next";

import { LegalPage } from "@/components/legal/LegalPage";

export const metadata: Metadata = {
  title: "DMCA & takedown",
  description:
    "ThumbIQ stores nothing, but rights holders can have a URL or channel permanently blocked from processing. Notices to dmca@thumbiq.app, acknowledged within 2 business days.",
};

export default function DmcaPage() {
  return (
    <LegalPage
      title="DMCA & takedown"
      updated="27 July 2026"
      intro="ThumbIQ does not host or store images. Cached entries expire within 60 minutes and a restart clears them immediately — so in most cases there is nothing to take down. Where a rights holder wants their content excluded from processing entirely, this is the process."
      sections={[
        {
          heading: "Send a notice",
          paragraphs: ["Email dmca@thumbiq.app including all of the following:"],
          bullets: [
            "Identification of the copyrighted work you are asserting rights in.",
            "The specific URL that produces it through ThumbIQ, or the channel or profile URL you want excluded.",
            "Your relationship to the work — owner, or authorised agent, and for whom.",
            "Contact details: name, email, and a physical address or business address.",
            "A statement that you have a good-faith belief the use is not authorised by the copyright owner, its agent, or the law.",
            "A statement, under penalty of perjury, that the information in your notice is accurate and that you are authorised to act on behalf of the owner.",
            "Your physical or electronic signature.",
          ],
        },
        {
          heading: "What happens next",
          table: {
            headers: ["Step", "Timing", "What we do"],
            rows: [
              ["Acknowledgement", "Within 2 business days", "We confirm receipt and give you a reference."],
              ["Cache purge", "Immediately on a valid notice", "Any cached copy is evicted. In practice it has usually already expired."],
              ["Processing blocklist", "Immediately on a valid notice", "The URL or channel is added to a permanent blocklist. ThumbIQ refuses to resolve it and returns a clear message to the user."],
              ["Response to you", "Within 5 business days", "We confirm what was done."],
            ],
          },
        },
        {
          heading: "Counter-notice",
          paragraphs: [
            "If you believe a blocklist entry was made in error, send a counter-notice to the same address with your contact details, identification of the blocked URL, and a statement under penalty of perjury that you have a good-faith belief the block resulted from a mistake or misidentification.",
            "Counter-notices are handled on the same timeline as notices, and both parties are told the outcome.",
          ],
        },
        {
          heading: "Why there is usually nothing to remove",
          paragraphs: [
            "ThumbIQ has no object store, no database and no permanent storage of any kind. Images live in a bounded in-memory cache for at most 60 minutes and are then evicted.",
            "There is no public gallery of processed thumbnails, and there will not be one — a gallery would turn a research tool into a redistribution service, which is the line this product does not cross.",
          ],
        },
        {
          heading: "Repeat infringers",
          paragraphs: [
            "ThumbIQ has no accounts, so there is no account to terminate. The available remedy is the processing blocklist, which is permanent and applies to everyone.",
          ],
        },
      ]}
    />
  );
}
