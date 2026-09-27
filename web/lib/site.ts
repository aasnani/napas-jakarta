const configuredSiteUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim();

export const SITE_URL = (configuredSiteUrl || "https://napasjakarta.armasn.dev").replace(/\/+$/, "");
export const SITE_NAME = "Napas Jakarta";
export const EN_GUIDE_PATH = "/air-quality-jakarta";
export const ID_GUIDE_PATH = "/id/kualitas-udara-jakarta";

export function absoluteUrl(path: string): string {
  return new URL(path, `${SITE_URL}/`).toString();
}
