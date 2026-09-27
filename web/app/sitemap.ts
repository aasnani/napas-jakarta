import type { MetadataRoute } from "next";
import { absoluteUrl, EN_GUIDE_PATH, ID_GUIDE_PATH } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const englishGuide = absoluteUrl(EN_GUIDE_PATH);
  const indonesianGuide = absoluteUrl(ID_GUIDE_PATH);
  const guideAlternates = { en: englishGuide, id: indonesianGuide };

  return [
    { url: absoluteUrl("/") },
    {
      url: englishGuide,
      alternates: { languages: guideAlternates },
    },
    {
      url: indonesianGuide,
      alternates: { languages: guideAlternates },
    },
  ];
}
