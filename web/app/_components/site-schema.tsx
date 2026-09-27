import { SITE_NAME, SITE_URL } from "@/lib/site";

const websiteSchema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      url: SITE_URL,
      description:
        "A bilingual Jakarta air-quality workspace with station-level readings and clear explanations of PM2.5, PM10, and Indonesia's ISPU index.",
      inLanguage: ["en", "id"],
    },
    {
      "@type": "WebApplication",
      "@id": `${SITE_URL}/#application`,
      name: SITE_NAME,
      url: SITE_URL,
      applicationCategory: "UtilitiesApplication",
      operatingSystem: "Web browser",
      isAccessibleForFree: true,
      isPartOf: { "@id": `${SITE_URL}/#website` },
      description:
        "Explore Jakarta station-level air-quality information and ask questions about pollutant measurements and ISPU.",
    },
  ],
};

export function SiteSchema() {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(websiteSchema).replace(/</g, "\\u003c"),
      }}
    />
  );
}
