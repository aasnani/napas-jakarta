import { NextResponse } from "next/server";
import { internalApiHeaders, napasApiOrigin } from "@/lib/server-api";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const apiOrigin = napasApiOrigin();
  if (!apiOrigin) {
    return NextResponse.json({ error: "station_data_unavailable" }, { status: 503 });
  }

  const requestedPollutant = new URL(request.url).searchParams.get("pollutant") ?? "PM2.5";
  const target = `${apiOrigin}/stations?pollutant=${encodeURIComponent(requestedPollutant)}`;

  try {
    const response = await fetch(target, {
      cache: "no-store",
      headers: internalApiHeaders(),
      signal: AbortSignal.timeout(8_000),
    });
    if (!response.ok) {
      return NextResponse.json({ error: "station_data_unavailable" }, { status: 502 });
    }
    return new NextResponse(await response.text(), {
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "station_data_unavailable" }, { status: 503 });
  }
}
