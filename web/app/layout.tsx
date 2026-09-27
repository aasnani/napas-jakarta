import type { Metadata } from "next";
import type { ReactNode } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "Napas Jakarta | Air Quality Monitor",
  description: "A conversational workspace for understanding Jakarta air quality.",
  icons: {
    icon: [{ url: "/napas-jakarta-air-icon.png", type: "image/png", sizes: "1254x1254" }],
    apple: "/napas-jakarta-air-icon.png",
  },
};

export default function RootLayout({ children }: { readonly children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
