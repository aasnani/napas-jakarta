"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Script from "next/script";
import { isPublicAnalyticsPath, sanitizeAnalyticsUrl } from "@/lib/analytics";

const MEASUREMENT_ID_PATTERN = /^G-[A-Z0-9]+$/;

export function isValidMeasurementId(value: string | undefined): value is string {
  return value !== undefined && MEASUREMENT_ID_PATTERN.test(value);
}

export function GoogleAnalytics({ measurementId }: { readonly measurementId: string }) {
  const pathname = usePathname() ?? "/";
  const [tagReady, setTagReady] = useState(false);

  useEffect(() => {
    if (
      !tagReady ||
      window.napasAnalyticsConsent !== "granted" ||
      !window.gtag ||
      !isPublicAnalyticsPath(pathname) ||
      !isPublicAnalyticsPath(window.location.pathname)
    ) {
      return;
    }

    const pageLocation = sanitizeAnalyticsUrl(window.location.href, true);
    const pageReferrer = sanitizeAnalyticsUrl(document.referrer);
    window.gtag("set", "page_location", pageLocation);
    window.gtag("set", "page_referrer", pageReferrer);
    window.gtag("event", "page_view", {
      page_path: pathname,
      page_location: pageLocation,
      page_referrer: pageReferrer,
      page_title: document.title,
    });
  }, [pathname, tagReady]);

  return (
    <>
      <Script id="napas-google-tag-init" strategy="afterInteractive">
        {`
          const savedConsent = window.napasAnalyticsConsent ?? window.localStorage.getItem('napas-analytics-consent');
          if (savedConsent === 'granted') {
            window.dataLayer = window.dataLayer || [];
            window.gtag = function(){window.dataLayer.push(arguments);};
            window.gtag('consent', 'default', {
              analytics_storage: 'granted',
              ad_storage: 'denied',
              ad_user_data: 'denied',
              ad_personalization: 'denied'
            });
            const pageLocation = window.location.origin + window.location.pathname;
            let pageReferrer = '';
            try {
              if (document.referrer) pageReferrer = new URL(document.referrer).origin;
            } catch {}
            window.gtag('set', 'page_location', pageLocation);
            window.gtag('set', 'page_referrer', pageReferrer);
            window.gtag('js', new Date());
            window.gtag('config', '${measurementId}', {
              send_page_view: false,
              page_location: pageLocation,
              page_referrer: pageReferrer,
              campaign_id: '',
              campaign_source: '',
              campaign_medium: '',
              campaign_name: '',
              campaign_term: '',
              campaign_content: '',
              allow_google_signals: false,
              allow_ad_personalization_signals: false
            });
          }
        `}
      </Script>
      <Script
        id="napas-google-tag"
        src={`https://www.googletagmanager.com/gtag/js?id=${measurementId}`}
        strategy="afterInteractive"
        onReady={() => setTagReady(true)}
      />
    </>
  );
}
