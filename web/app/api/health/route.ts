import { NextResponse } from "next/server";
import { probeEveHealth } from "@/lib/eve-health";

export const dynamic = "force-dynamic";

export async function GET() {
  const eveReady = await probeEveHealth();
  return NextResponse.json(
    {
      dependencies: { eve: eveReady ? "ready" : "unavailable" },
      service: "napas-web",
      status: eveReady ? "ok" : "degraded",
    },
    {
      headers: { "Cache-Control": "no-store" },
      status: eveReady ? 200 : 503,
    },
  );
}
