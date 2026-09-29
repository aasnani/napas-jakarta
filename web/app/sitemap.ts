import type { MetadataRoute } from "next";
import {
  absoluteUrl,
  EN_ABOUT_PATH,
  EN_GUIDE_PATH,
  EN_PRIVACY_PATH,
  ID_ABOUT_PATH,
  ID_GUIDE_PATH,
  ID_PRIVACY_PATH,
} from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const englishGuide = absoluteUrl(EN_GUIDE_PATH);
  const indonesianGuide = absoluteUrl(ID_GUIDE_PATH);
  const englishAbout = absoluteUrl(EN_ABOUT_PATH);
  const indonesianAbout = absoluteUrl(ID_ABOUT_PATH);
  const englishPrivacy = absoluteUrl(EN_PRIVACY_PATH);
  const indonesianPrivacy = absoluteUrl(ID_PRIVACY_PATH);
  const guideAlternates = { en: englishGuide, id: indonesianGuide, "x-default": englishGuide };
  const aboutAlternates = { en: englishAbout, id: indonesianAbout, "x-default": englishAbout };
  const privacyAlternates = { en: englishPrivacy, id: indonesianPrivacy, "x-default": englishPrivacy };

  return [
    { url: absoluteUrl("/") },
    { url: englishAbout, alternates: { languages: aboutAlternates } },
    { url: indonesianAbout, alternates: { languages: aboutAlternates } },
    { url: englishPrivacy, alternates: { languages: privacyAlternates } },
    { url: indonesianPrivacy, alternates: { languages: privacyAlternates } },
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
