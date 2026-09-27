import type { Metadata } from "next";
import { ABOUT_PATHS, PublicInfoLayout } from "@/app/_components/public-info-layout";
import styles from "@/app/_components/guide-layout.module.css";
import { absoluteUrl } from "@/lib/site";
import { getUiCopy } from "@/lib/i18n";

const copy = getUiCopy("id");
const title = "Tentang Napas Jakarta | Monitor Kualitas Udara";
const description = copy.about.aboutBody[0];

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: absoluteUrl(ABOUT_PATHS.id),
    languages: {
      en: absoluteUrl(ABOUT_PATHS.en),
      id: absoluteUrl(ABOUT_PATHS.id),
    },
  },
  openGraph: { type: "website", locale: "id_ID", title, description, url: absoluteUrl(ABOUT_PATHS.id) },
  twitter: { card: "summary", title, description },
};

export default function HalamanTentang() {
  return (
    <PublicInfoLayout lang="id" localizedPaths={ABOUT_PATHS}>
      <p className={styles.eyebrow}>{copy.about.kicker}</p>
      <h1 className={styles.title}>{copy.about.aboutTitle}</h1>
      <section aria-label="Tentang Napas Jakarta" className={styles.section}>
        {copy.about.aboutBody.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
      </section>
    </PublicInfoLayout>
  );
}
