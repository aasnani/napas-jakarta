import type { Metadata } from "next";
import { JsonLd } from "@/app/_components/site-schema";
import { homeSchema } from "@/lib/guide-content";
import { Workspace } from "@/app/_components/workspace";
import { EN_HOME_PATH, ID_HOME_PATH } from "@/lib/site";

const title = "Peta Kualitas Udara Jakarta: PM2.5 & ISPU | Napas Jakarta";
const description =
  "Jelajahi pembacaan kualitas udara per stasiun di Jakarta, beserta penjelasan PM2.5, PM10, ISPU, sumber data, dan kesegaran data, dalam bahasa Indonesia dan Inggris.";

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: ID_HOME_PATH,
    languages: { en: EN_HOME_PATH, id: ID_HOME_PATH, "x-default": EN_HOME_PATH },
  },
  openGraph: {
    type: "website",
    siteName: "Napas Jakarta",
    locale: "id_ID",
    title,
    description,
    url: ID_HOME_PATH,
    images: [
      {
        url: "/napas-jakarta-air-icon.png",
        width: 1254,
        height: 1254,
        alt: "Ikon kualitas udara Napas Jakarta",
      },
    ],
  },
  twitter: { card: "summary_large_image", title, description, images: ["/napas-jakarta-air-icon.png"] },
};

export default function IndonesianHomePage() {
  return (
    <>
      <JsonLd data={homeSchema("id")} />
      <Workspace initialLanguage="id" />
    </>
  );
}
