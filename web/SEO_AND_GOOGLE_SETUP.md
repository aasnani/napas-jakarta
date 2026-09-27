# Napas Jakarta search and analytics setup

This setup is for Napas Jakarta's own site and GA4 property. The current public
domain recorded for the project is `napasjakarta.armasn.dev`.

## Current baseline

The production homepage responds successfully. At the last public check, its
HTML used the generic description “A conversational workspace for understanding
Jakarta air quality,” and `/sitemap.xml` returned 404. The web code now defines
canonical metadata, an XML sitemap, a sitemap-linked robots file, and paired
English and Indonesian air-quality guides.

Confirm the deployed commit and Railway deployment after publishing these
changes; merging code alone does not prove that production has updated.

## Google Search Console

1. Open the existing Search Console **Domain property** for
   `napasjakarta.armasn.dev` using the Google account that owns it. Confirm its
   status is verified; if it is already verified, no token or DNS change is
   needed. If Search Console shows verification is still pending, follow the
   method shown for that property.
2. Submit `https://napasjakarta.armasn.dev/sitemap.xml` under **Sitemaps**.
   Use URL inspection for the homepage and both guide pages:
   - `https://napasjakarta.armasn.dev/`
   - `https://napasjakarta.armasn.dev/air-quality-jakarta`
   - `https://napasjakarta.armasn.dev/id/kualitas-udara-jakarta`
3. In **Settings → Search generative AI**, verify Napas is included in Google
   Search's generative AI features. If the property inherits a parent setting,
   confirm that setting is also inclusion. Google says inclusion is the default
   for a property that does not inherit an exclusion.

Domain properties cover their subdomains and protocols; `napasjakarta.armasn.dev`
does not merge data with a separate `armasn.dev` property. See Google's
[property setup guide](https://support.google.com/webmasters/answer/34592?hl=en)
and [Search generative AI control](https://support.google.com/webmasters/answer/16908024).

## Google Analytics 4

1. The Napas web code is configured with measurement ID `G-H242BLRQXX`. Confirm
   that it belongs to a web stream in the separate **Napas Jakarta** GA4
   property for `https://napasjakarta.armasn.dev`, not the ServersUp property.
   If needed, create a separate property and web stream before linking it.
2. This measurement ID is a public ID, not a password or API secret. The optional
   `NEXT_PUBLIC_GA_MEASUREMENT_ID` build variable overrides that default; if
   Railway already defines it, make sure it matches this Napas stream. Rebuild
   and deploy the web service after changing the value.
3. Analytics loads only after a visitor chooses **Allow analytics**. A visitor
   who declines before opting in does not load the Google tag. If a visitor
   later revokes consent through **Privacy choices**, the app stops sending its
   manual page-view and interaction events and updates Google's consent state.
4. The code sends page views for the public homepage and the two guides, plus
   `assistant_question_submitted` and `station_selected` events. It sends no
   prompt text, attachments, station name, session ID, or query string. Ads
   storage, Google signals, and ads personalization are disabled.
5. In the GA4 web stream, turn off Enhanced Measurement's **Page changes based
   on browser history events** option. The app sends its own page views for the
   public pages; the setting avoids duplicate views and keeps tracking limited
   to the explicit public-page list.
6. Test with an explicit opt-in: open the public homepage, use the map, submit a
   question, and visit both guides. Confirm the events in **Realtime**. Repeat
   after declining and confirm no Google Analytics events are sent.

Google's current setup steps are in its [GA4 website setup guide](https://support.google.com/analytics/answer/14183469?hl=en).

## Link the two Google properties

After Search Console ownership is verified and the GA4 property is created,
link them in **GA4 Admin → Product links → Search Console Links**. Google
requires a verified Search Console owner and Editor access to the Analytics
property. Keep the Napas Search Console property and Napas GA4 property
selected; this link does not combine Napas and ServersUp data. See Google's
[linking instructions](https://support.google.com/analytics/answer/10737381?hl=en).

## SEO and answer-search content plan

### Napas's audience and job

Napas is a bilingual Jakarta air-quality map and assistant. Its practical
audiences are Jakarta residents and commuters who want to understand a station
reading, and people who need a clear explanation of PM2.5, PM10, ISPU, data
timestamps, or sources. The core job is to help them interpret a reading and
reach its source, not to present one monitor as a city-wide average.

### Search topics to start with

- English: Jakarta air quality, Jakarta air quality map, Jakarta PM2.5, Jakarta
  ISPU, how to read an air-quality station reading.
- Indonesian: kualitas udara Jakarta, ISPU Jakarta, PM2.5 Jakarta, cara membaca
  data kualitas udara, stasiun pemantau kualitas udara Jakarta.

These are intent themes, not claims about search volume. Use Search Console
queries and landing-page performance to refine them after indexing.

### Pages and next content

- **Available now:** the workspace homepage and a sourced guide in each
  language, with reciprocal language links and self-canonicals.
- **Next:** a data-source and freshness page, once the exact update cadence,
  station coverage, and fallback behavior can be stated for users.
- **Then:** a station coverage explainer with official source links and dates;
  create individual station pages only when each has stable, useful, distinct
  information.
- **Later:** an exposure-guidance page only with carefully sourced official
  health guidance and a clear editorial review process.

Do not create thin district or station pages solely to repeat keywords. Google
says its AI Search features use the same core Search practices: useful original
content, crawlability, and clear organization. Google does not require a special
AI file or schema for AI Overviews or AI Mode. The guides use direct answers,
ordinary question headings, visible government and WHO sources, and structured
HTML for readers and answer engines. See [Google's guide to generative AI
features](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide).

### How to review progress

- Search Console: indexing of the three public URLs, search queries, impressions,
  clicks, and click-through rate for both English and Indonesian topics.
- GA4: opted-in public-page views, map station selections, assistant question
  starts, and referrals. Never treat low opt-in volume as total site traffic.
- After each release: verify the deployed commit, homepage, both guide URLs,
  `/robots.txt`, and `/sitemap.xml` on the live domain.
