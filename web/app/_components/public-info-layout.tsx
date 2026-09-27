import type { ReactNode } from "react";
import Link from "next/link";
import { EN_ABOUT_PATH, EN_GUIDE_PATH, EN_PRIVACY_PATH, ID_ABOUT_PATH, ID_GUIDE_PATH, ID_PRIVACY_PATH } from "@/lib/site";
import styles from "./guide-layout.module.css";

export function PublicInfoLayout({
  children,
  lang,
  localizedPaths,
}: {
  readonly children: ReactNode;
  readonly lang: "en" | "id";
  readonly localizedPaths: { readonly en: string; readonly id: string };
}) {
  const isEnglish = lang === "en";
  const guidePath = isEnglish ? EN_GUIDE_PATH : ID_GUIDE_PATH;

  return (
    <main className={styles.page} lang={lang}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/">Napas Jakarta</Link>
        <nav aria-label={isEnglish ? "Choose language" : "Pilih bahasa"} className={styles.languages}>
          <Link aria-current={isEnglish ? "page" : undefined} href={localizedPaths.en} lang="en">English</Link>
          <Link aria-current={!isEnglish ? "page" : undefined} href={localizedPaths.id} lang="id">Bahasa Indonesia</Link>
        </nav>
      </header>
      <article className={styles.article} lang={lang}>
        {children}
        <nav aria-label={isEnglish ? "Related pages" : "Halaman terkait"} className={styles.related}>
          <Link href="/">{isEnglish ? "Open the Napas Jakarta workspace" : "Buka ruang kerja Napas Jakarta"}</Link>
          <Link href={guidePath} lang={lang}>
            {isEnglish ? "Jakarta air-quality guide" : "Panduan kualitas udara Jakarta"}
          </Link>
        </nav>
      </article>
      <footer className={styles.footer}>
        {isEnglish
          ? "Napas Jakarta is a bilingual map and assistant for understanding Jakarta air quality."
          : "Napas Jakarta adalah peta dan asisten dwibahasa untuk memahami kualitas udara Jakarta."}
      </footer>
    </main>
  );
}

export const ABOUT_PATHS = { en: EN_ABOUT_PATH, id: ID_ABOUT_PATH } as const;
export const PRIVACY_PATHS = { en: EN_PRIVACY_PATH, id: ID_PRIVACY_PATH } as const;
