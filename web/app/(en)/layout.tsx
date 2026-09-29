import type { Metadata } from "next";
import type { ReactNode } from "react";
import { RootShell } from "@/app/_components/root-shell";
import { SITE_URL } from "@/lib/site";

const description =
  "Explore Jakarta station-level air-quality readings and clear explanations of PM2.5, PM10, ISPU, sources, and data freshness—in English and Indonesian.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "Napas Jakarta | Air Quality Monitor",
  description,
  applicationName: "Napas Jakarta",
  alternates: { canonical: "/" },
  robots: { index: true, follow: true },
  openGraph: {
    type: "website",
    siteName: "Napas Jakarta",
    title: "Jakarta Air Quality Map & ISPU Guide | Napas Jakarta",
    description,
    url: "/",
    images: [
      {
        url: "/napas-jakarta-air-icon.png",
        width: 1254,
        height: 1254,
        alt: "Napas Jakarta air-quality icon",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Jakarta Air Quality Map & ISPU Guide | Napas Jakarta",
    description,
    images: ["/napas-jakarta-air-icon.png"],
  },
  icons: {
    icon: [{ url: "/napas-jakarta-air-icon.png", type: "image/png", sizes: "1254x1254" }],
    apple: "/napas-jakarta-air-icon.png",
  },
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return <RootShell lang="en">{children}</RootShell>;
}
