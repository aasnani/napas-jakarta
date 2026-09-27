"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { LANGUAGE_CHANGE_EVENT, LANGUAGE_STORAGE_KEY } from "@/lib/i18n";
import { isPublicAnalyticsPath } from "@/lib/analytics";
import { GoogleAnalytics, isValidMeasurementId } from "./google-analytics";
import styles from "./analytics-consent.module.css";

type ConsentChoice = "granted" | "denied";

const CONSENT_STORAGE_KEY = "napas-analytics-consent";
const MEASUREMENT_ID =
  process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim() || "G-H242BLRQXX";

export function AnalyticsConsent() {
  const pathname = usePathname() ?? "/";
  const [choice, setChoice] = useState<ConsentChoice | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [browserLocationIsPublic, setBrowserLocationIsPublic] = useState(false);
  const [isIndonesian, setIsIndonesian] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(CONSENT_STORAGE_KEY);
      if (stored === "granted" || stored === "denied") {
        window.napasAnalyticsConsent = stored;
        setChoice(stored);
      } else {
        window.napasAnalyticsConsent = null;
        setSettingsOpen(true);
      }
    } catch {
      window.napasAnalyticsConsent = null;
      setSettingsOpen(true);
    }
  }, []);

  useEffect(() => {
    setBrowserLocationIsPublic(isPublicAnalyticsPath(window.location.pathname));
  }, [pathname]);

  useEffect(() => {
    const updateLanguage = () => {
      if (pathname.startsWith("/id/")) {
        setIsIndonesian(true);
        return;
      }
      try {
        setIsIndonesian(window.localStorage.getItem(LANGUAGE_STORAGE_KEY) === "id");
      } catch {
        setIsIndonesian(document.documentElement.lang === "id");
      }
    };

    updateLanguage();
    window.addEventListener(LANGUAGE_CHANGE_EVENT, updateLanguage);
    return () => window.removeEventListener(LANGUAGE_CHANGE_EVENT, updateLanguage);
  }, [pathname]);

  useEffect(() => {
    if (!window.gtag || choice === null) return;
    const mayMeasureThisRoute =
      choice === "granted" &&
      isPublicAnalyticsPath(pathname) &&
      isPublicAnalyticsPath(window.location.pathname);
    window.gtag("consent", "update", {
      analytics_storage: mayMeasureThisRoute ? "granted" : "denied",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    });
  }, [choice, pathname]);

  if (!isValidMeasurementId(MEASUREMENT_ID) || !isPublicAnalyticsPath(pathname)) return null;

  function saveChoice(nextChoice: ConsentChoice) {
    setBrowserLocationIsPublic(isPublicAnalyticsPath(window.location.pathname));
    window.napasAnalyticsConsent = nextChoice;
    setChoice(nextChoice);
    setSettingsOpen(false);
    try {
      window.localStorage.setItem(CONSENT_STORAGE_KEY, nextChoice);
    } catch {
      // Keep the current-page choice if storage is unavailable.
    }
    window.gtag?.("consent", "update", {
      analytics_storage: nextChoice === "granted" ? "granted" : "denied",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
    });
  }

  const canLoadTag =
    choice === "granted" &&
    browserLocationIsPublic &&
    isPublicAnalyticsPath(pathname);

  return (
    <>
      {canLoadTag ? <GoogleAnalytics measurementId={MEASUREMENT_ID} /> : null}
      {settingsOpen ? (
        <section aria-labelledby="analytics-consent-title" className={styles.notice} role="region">
          <h2 className={styles.title} id="analytics-consent-title">
            {isIndonesian ? "Pilihan analitik" : "Analytics choices"}
          </h2>
          <p className={styles.copy}>
            {isIndonesian
              ? "Izinkan Google Analytics mengukur kunjungan dan penggunaan peta serta asisten. Kami tidak mengirim teks percakapan, tautan sesi, nama stasiun, atau parameter URL. Tag Google hanya dimuat setelah Anda menyetujui; Anda dapat mengubah pilihan ini kapan saja."
              : "Allow Google Analytics to measure visits and use of the map and assistant. We do not send chat text, session links, station names, or URL parameters. Google tags load only after you opt in; you can change this choice at any time."}
          </p>
          <div className={styles.actions}>
            <button className={styles.allow} onClick={() => saveChoice("granted")} type="button">
              {isIndonesian ? "Izinkan analitik" : "Allow analytics"}
            </button>
            <button className={styles.decline} onClick={() => saveChoice("denied")} type="button">
              {isIndonesian ? "Tolak" : "Decline"}
            </button>
          </div>
        </section>
      ) : (
        <button
          className={styles.preferences}
          onClick={() => {
            setBrowserLocationIsPublic(isPublicAnalyticsPath(window.location.pathname));
            setSettingsOpen(true);
          }}
          type="button"
        >
          {isIndonesian ? "Pilihan privasi" : "Privacy choices"}
        </button>
      )}
    </>
  );
}
