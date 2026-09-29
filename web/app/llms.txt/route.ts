import { absoluteUrl, EN_ABOUT_PATH, EN_GUIDE_PATH, ID_ABOUT_PATH, ID_GUIDE_PATH, SITE_NAME } from "@/lib/site";

export const dynamic = "force-static";

const body = `# ${SITE_NAME}

> Napas Jakarta is a bilingual (English and Indonesian) Jakarta air-quality map and assistant. It shows station-level readings from the official DKI Jakarta air-quality monitoring network and explains PM2.5, PM10 and ISPU in plain language.

## Guides

- [Jakarta air quality: PM2.5, PM10 and ISPU explained](${absoluteUrl(EN_GUIDE_PATH)}): English guide with sources
- [Kualitas udara Jakarta: memahami PM2.5, PM10, dan ISPU](${absoluteUrl(ID_GUIDE_PATH)}): panduan berbahasa Indonesia

## App and about

- [Jakarta air quality map and assistant (English)](${absoluteUrl("/")})
- [Peta kualitas udara Jakarta (Indonesia)](${absoluteUrl("/id")})
- [About Napas Jakarta](${absoluteUrl(EN_ABOUT_PATH)})
- [Tentang Napas Jakarta](${absoluteUrl(ID_ABOUT_PATH)})

## Data provenance and freshness

- Station readings come from the official DKI Jakarta air-quality monitoring portal (https://udara.jakarta.go.id/). Each reading belongs to one station and one observation time.
- A station reading is not a city-wide average. Compare several stations and their timestamps.
- Readings older than 24 hours are treated as stale and are not presented as current conditions.
- ISPU is Indonesia's unitless air-quality index; PM2.5 and PM10 are particle concentrations (µg/m³). They are different kinds of value.
- Live values change; always check the observation time and follow the source link.

## How to cite

Cite the specific page URL and name "Napas Jakarta" as the explainer. For a live reading, cite the official DKI Jakarta portal as the data source and include the station name and observation time shown there.
`;

export function GET() {
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
