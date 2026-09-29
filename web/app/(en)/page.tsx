import type { Metadata } from "next";
import { JsonLd } from "@/app/_components/site-schema";
import { homeSchema } from "@/lib/guide-content";
import { Workspace } from "@/app/_components/workspace";
import { EN_HOME_PATH, ID_HOME_PATH } from "@/lib/site";

export const metadata: Metadata = {
  alternates: {
    canonical: EN_HOME_PATH,
    languages: { en: EN_HOME_PATH, id: ID_HOME_PATH, "x-default": EN_HOME_PATH },
  },
};

export default function Page() {
  return (
    <>
      <JsonLd data={homeSchema("en")} />
      <Workspace initialLanguage="en" />
    </>
  );
}
