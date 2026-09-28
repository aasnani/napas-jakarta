"use client";

import Link from "next/link";
import { getUiCopy, type Language } from "@/lib/i18n";
import {
  EN_ABOUT_PATH,
  EN_GUIDE_PATH,
  EN_PRIVACY_PATH,
  ID_ABOUT_PATH,
  ID_GUIDE_PATH,
  ID_PRIVACY_PATH,
} from "@/lib/site";

export function SiteHeader({
  language,
  localizedPaths,
  onLanguageChange,
}: {
  readonly language: Language;
  readonly localizedPaths?: { readonly en: string; readonly id: string };
  readonly onLanguageChange?: (language: Language) => void;
}) {
  const copy = getUiCopy(language);

  return (
    <header className="topbar" data-od-id="top-navbar">
      <div className="topbar-left">
        <div aria-label={copy.navbar.monitor} className="topbar-side">
          <span className="topbar-label-full">{copy.navbar.monitor}</span>
          <span className="topbar-label-mobile">{copy.navbar.mobileMonitor}</span>
        </div>
        <nav aria-label={copy.navbar.productInformation} className="topbar-actions">
          <Link className="topbar-link" href={language === "id" ? ID_ABOUT_PATH : EN_ABOUT_PATH} lang={language}>{copy.navbar.about}</Link>
          <Link aria-label={copy.navbar.airQualityGuide} className="topbar-link" href={language === "id" ? ID_GUIDE_PATH : EN_GUIDE_PATH} lang={language}>{copy.navbar.guide}</Link>
          <Link className="topbar-link" href={language === "id" ? ID_PRIVACY_PATH : EN_PRIVACY_PATH} lang={language}>{copy.navbar.privacy}</Link>
        </nav>
      </div>
      <Link aria-label={copy.navbar.brandHome} className="brand" href="/" data-od-id="napas-logo">
        <img alt="" height={1254} src="/napas-jakarta-air-icon.png" width={1254} />
        <span className="brand-title">Napas <small>Jakarta</small></span>
      </Link>
      <div className="topbar-right">
        <div aria-label={copy.navbar.language} className="language-toggle" role="group">
          {onLanguageChange ? (
            <>
              <button aria-label={copy.navbar.switchEnglish} aria-pressed={language === "en"} className={language === "en" ? "is-active" : undefined} onClick={() => onLanguageChange("en")} type="button">EN</button>
              <button aria-label={copy.navbar.switchIndonesian} aria-pressed={language === "id"} className={language === "id" ? "is-active" : undefined} onClick={() => onLanguageChange("id")} type="button">ID</button>
            </>
          ) : (
            <>
              <Link aria-current={language === "en" ? "page" : undefined} aria-label={copy.navbar.switchEnglish} className={language === "en" ? "is-active" : undefined} href={localizedPaths?.en ?? "/"} lang="en">EN</Link>
              <Link aria-current={language === "id" ? "page" : undefined} aria-label={copy.navbar.switchIndonesian} className={language === "id" ? "is-active" : undefined} href={localizedPaths?.id ?? "/"} lang="id">ID</Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
