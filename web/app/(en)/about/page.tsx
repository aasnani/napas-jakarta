import type { Metadata } from "next";
import { PublicInfoLayout, ABOUT_PATHS } from "@/app/_components/public-info-layout";
import styles from "@/app/_components/guide-layout.module.css";
import { AboutContent } from "@/app/_components/about-content";
import { JsonLd } from "@/app/_components/site-schema";
import { pageSchema } from "@/lib/guide-content";
import { absoluteUrl } from "@/lib/site";
import { getUiCopy } from "@/lib/i18n";

const copy = getUiCopy("en");
const title = "About Napas Jakarta | Air Quality Monitor";
const description =
  "Napas Jakarta is a conversational guide to Jakarta air quality, bringing the map, station readings and plain-language explanations together in one place.";

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: absoluteUrl(ABOUT_PATHS.en),
    languages: {
      en: absoluteUrl(ABOUT_PATHS.en),
      "x-default": absoluteUrl(ABOUT_PATHS.en),
      id: absoluteUrl(ABOUT_PATHS.id),
    },
  },
  openGraph: { type: "website", locale: "en_ID", title, description, url: absoluteUrl(ABOUT_PATHS.en) },
  twitter: { card: "summary", title, description },
};

export default function AboutPage() {
  return (
    <PublicInfoLayout lang="en" localizedPaths={ABOUT_PATHS}>
      <JsonLd data={pageSchema("en", "AboutPage", title, description, ABOUT_PATHS.en)} />
      <p className={styles.eyebrow}>{copy.about.kicker}</p>
      <h1 className={styles.title}>{copy.about.aboutTitle}</h1>
      <AboutContent lang="en" />
    </PublicInfoLayout>
  );
}
