import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json(
    { service: "napas-web", status: "ok" },
    { headers: { "Cache-Control": "no-store" } },
  );
}
