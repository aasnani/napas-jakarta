import type { NextConfig } from "next";
import { withEve } from "eve/next";

const nextConfig: NextConfig = {
  // Eve emits a long-lived event stream. Keep Next from applying response
  // compression or other transformations that can delay client-visible
  // deltas, especially in local and self-hosted deployments.
  compress: false,
  experimental: {
    // Keep the Eve chat request bounded even when a client omits
    // Content-Length and the application proxy cannot reject it early.
    proxyClientMaxBodySize: "128kb",
  },
  // The in-app browser uses the loopback IP during local development. Allow
  // Next's client resources and HMR to hydrate normally on that origin.
  allowedDevOrigins: ["127.0.0.1"],
  async headers() {
    return [
      {
        source: "/eve/:path*",
        headers: [
          { key: "Cache-Control", value: "no-store, no-transform" },
          { key: "X-Accel-Buffering", value: "no" },
        ],
      },
    ];
  },
};

export default withEve(nextConfig);
