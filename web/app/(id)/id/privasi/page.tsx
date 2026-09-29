import type { Metadata } from "next";
import { PublicInfoLayout, PRIVACY_PATHS } from "@/app/_components/public-info-layout";
import { PrivacyChoicesButton } from "@/app/_components/analytics-consent";
import styles from "@/app/_components/guide-layout.module.css";
import { JsonLd } from "@/app/_components/site-schema";
import { pageSchema } from "@/lib/guide-content";
import { absoluteUrl } from "@/lib/site";
import { getUiCopy } from "@/lib/i18n";

const copy = getUiCopy("id");
const title = "Privasi | Napas Jakarta";
const description = "Cara Napas Jakarta menangani pertanyaan chat, telemetri produk, dan Google Analytics dengan persetujuan Anda, serta cara mengubah pilihan analitik kapan saja.";

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: absoluteUrl(PRIVACY_PATHS.id),
    languages: {
      en: absoluteUrl(PRIVACY_PATHS.en),
      "x-default": absoluteUrl(PRIVACY_PATHS.en),
      id: absoluteUrl(PRIVACY_PATHS.id),
    },
  },
};

export default function HalamanPrivasi() {
  const body = copy.about.privacyBody;
  return (
    <PublicInfoLayout lang="id" localizedPaths={PRIVACY_PATHS}>
      <JsonLd data={pageSchema("id", "WebPage", title, description, PRIVACY_PATHS.id)} />
      <p className={styles.eyebrow}>{copy.about.kicker}</p>
      <h1 className={styles.title}>{copy.about.privacyTitle}</h1>
      <section aria-label="Privasi Napas Jakarta" className={styles.section}>
        <p>{body[0]}</p>
        <p>{body[1]}</p>
        <ul>{body.slice(2, 5).map((paragraph) => <li key={paragraph}>{paragraph}</li>)}</ul>
        <p>{body[5]}</p>
        <p>{body[6]}</p>
      </section>
      <PrivacyChoicesButton language="id" />
    </PublicInfoLayout>
  );
}
