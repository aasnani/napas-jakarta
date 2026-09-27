import type { ReactNode } from "react";
import Link from "next/link";
import { EN_GUIDE_PATH, ID_GUIDE_PATH } from "@/lib/site";
import styles from "./guide-layout.module.css";

export function GuideLayout({
  lang,
  children,
}: {
  readonly lang: "en" | "id";
  readonly children: ReactNode;
}) {
  const isEnglish = lang === "en";

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/">Napas Jakarta</Link>
        <nav aria-label={isEnglish ? "Choose language" : "Pilih bahasa"} className={styles.languages}>
          <Link aria-current={isEnglish ? "page" : undefined} href={EN_GUIDE_PATH} lang="en">
            English
          </Link>
          <Link aria-current={!isEnglish ? "page" : undefined} href={ID_GUIDE_PATH} lang="id">
            Bahasa Indonesia
          </Link>
        </nav>
      </header>
      <article className={styles.article} lang={lang}>
        {children}
        <nav aria-label={isEnglish ? "Related pages" : "Halaman terkait"} className={styles.related}>
          <Link href="/">
            {isEnglish ? "Open the Napas Jakarta workspace" : "Buka ruang kerja Napas Jakarta"}
          </Link>
          <Link href={isEnglish ? ID_GUIDE_PATH : EN_GUIDE_PATH} lang={isEnglish ? "id" : "en"}>
            {isEnglish ? "Baca dalam Bahasa Indonesia" : "Read in English"}
          </Link>
        </nav>
      </article>
      <footer className={styles.footer}>
        {isEnglish
          ? "Napas Jakarta explains station-level air-quality information. Check each reading's time and source before using it."
          : "Napas Jakarta menjelaskan informasi kualitas udara per stasiun. Periksa waktu dan sumber setiap pengamatan sebelum menggunakannya."}
      </footer>
    </main>
  );
}
