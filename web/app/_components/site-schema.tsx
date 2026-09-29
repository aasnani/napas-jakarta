import { OPERATOR_SAME_AS } from "@/lib/guide-content";
import { SITE_NAME, SITE_URL } from "@/lib/site";

export function JsonLd({ data }: { readonly data: unknown }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}

const siteSchema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: SITE_NAME,
      url: SITE_URL,
      logo: `${SITE_URL}/napas-jakarta-air-icon.png`,
      sameAs: OPERATOR_SAME_AS,
    },
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      url: SITE_URL,
      description:
        "A bilingual Jakarta air-quality workspace with station-level readings and clear explanations of PM2.5, PM10, and Indonesia's ISPU index.",
      inLanguage: ["en", "id"],
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
  ],
};

export function SiteSchema() {
  return <JsonLd data={siteSchema} />;
}
