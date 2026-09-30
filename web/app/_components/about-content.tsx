import Link from "next/link";
import { ABOUT_CONTENT } from "@/lib/about-content";
import { EN_GUIDE_PATH, EN_PRIVACY_PATH, ID_GUIDE_PATH, ID_PRIVACY_PATH } from "@/lib/site";
import styles from "./guide-layout.module.css";

export function AboutContent({ lang }: { readonly lang: "en" | "id" }) {
  const content = ABOUT_CONTENT[lang];
  const guidePath = lang === "id" ? ID_GUIDE_PATH : EN_GUIDE_PATH;
  const privacyPath = lang === "id" ? ID_PRIVACY_PATH : EN_PRIVACY_PATH;

  return (
    <>
      <p className={styles.intro}>{content.intro}</p>
      {content.sections.map((section) => (
        <section aria-labelledby={section.id} className={styles.section} key={section.id}>
          <h2 id={section.id}>{section.heading}</h2>
          {section.paragraphs?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          {section.bullets ? (
            <ul>{section.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}</ul>
          ) : null}
        </section>
      ))}
      <section aria-label={content.guideLabel} className={styles.section}>
        <ul className={styles.sources}>
          <li><Link href={guidePath} lang={lang}>{content.guideLabel}</Link></li>
          <li>
            <a href="https://udara.jakarta.go.id/" rel="noreferrer" target="_blank">{content.portalLabel}</a>
          </li>
          <li><Link href={privacyPath} lang={lang}>{content.privacyLabel}</Link></li>
        </ul>
      </section>
    </>
  );
}
