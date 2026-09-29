import type { Metadata } from "next";
import type { ReactNode } from "react";
import { RootShell } from "@/app/_components/root-shell";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  applicationName: "Napas Jakarta",
  robots: { index: true, follow: true },
  icons: {
    icon: [{ url: "/napas-jakarta-air-icon.png", type: "image/png", sizes: "1254x1254" }],
    apple: "/napas-jakarta-air-icon.png",
  },
};

export default function IndonesianRootLayout({ children }: { readonly children: ReactNode }) {
  return <RootShell lang="id">{children}</RootShell>;
}
