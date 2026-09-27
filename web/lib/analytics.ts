export type NapasAnalyticsEvent = "assistant_question_submitted" | "station_selected";

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
    napasAnalyticsConsent?: "granted" | "denied" | null;
  }
}

const SESSION_PATH = /^\/s(?:\/|$)/;

export function isPublicAnalyticsPath(pathname: string): boolean {
  return ["/", "/air-quality-jakarta", "/id/kualitas-udara-jakarta"].includes(pathname);
}

export function trackNapasEvent(eventName: NapasAnalyticsEvent): void {
  if (
    typeof window === "undefined" ||
    window.napasAnalyticsConsent !== "granted" ||
    !window.gtag ||
    SESSION_PATH.test(window.location.pathname)
  ) {
    return;
  }

  // Deliberately send no question text, station name, session ID, or URL parameters.
  window.gtag("event", eventName);
}

export function suspendAnalyticsForSession(): void {
  if (typeof window === "undefined" || !window.gtag) return;

  window.gtag("consent", "update", {
    analytics_storage: "denied",
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
  });
}
