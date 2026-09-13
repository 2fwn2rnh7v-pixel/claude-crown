# Measurement, Monitoring and Traffic-Drop Diagnosis

## Contents
- The instrument panel
- Search Console reports and what each answers
- Analytics: organic without lying
- Branded vs non-branded
- Traffic-drop diagnosis, in order
- Monitoring cadence
- Reporting rules
- Sources

---

## The instrument panel

| Question | Instrument |
|---|---|
| Is the page indexed, how does Google see it | Search Console URL Inspection (crawled HTML, screenshot, live test) |
| Which pages are excluded and why | Search Console → Pages (indexing) |
| Impressions, clicks, CTR, position per query/page | Search Console → Performance → Web |
| Visibility in AI Overviews / AI Mode | Search Console → Performance → Generative AI (impressions only) |
| Rich result errors | Search Console → Enhancements |
| Field performance | Search Console → Core Web Vitals; PageSpeed Insights (CrUX) |
| Manual actions, security issues | Search Console → Manual actions / Security |
| Sessions, conversions, landing pages | GA4 (or a privacy-first alternative) |
| Crawler behaviour and edge blocks | Server or CDN logs by user agent and status |
| Bing/Copilot/ChatGPT retrieval | Bing Webmaster Tools (index, IndexNow, crawl errors) |
| Local | Business Profile Performance |

## Search Console reports and what each answers

- **Performance → Web**: 16 months of data. Compare periods, filter by page, query, country,
  device. Position is the average of the top position per impression, so a new query at
  position 50 drags the average down while total clicks rise; always read clicks and
  impressions before position.
- **Performance → Generative AI** (worldwide since 2026-08-31): impressions in AI Overviews,
  AI Mode and Discover AI features by page, country, device, date. No clicks, no queries.
  Clicks from AI features are inside the Web numbers. Treat it as a reach indicator.
- **Pages (indexing)**: every exclusion reason is a to-do or a deliberate decision.
  "Crawled, currently not indexed" = quality or duplication judgement; "Discovered, currently
  not indexed" = crawl budget or low priority; "Excluded by noindex", "Blocked by robots.txt",
  "Alternate page with proper canonical", "Soft 404", "Redirect error". Validate fixes here.
- **Sitemaps**: submitted vs discovered vs indexed. A big gap between discovered and indexed
  is the quality signal to act on.
- **URL Inspection**: the single most useful tool. Shows the last crawl, the rendered HTML,
  the canonical Google chose vs the one declared, mobile usability, structured data detected.
  Live Test shows what a crawl would see right now, including CDN blocks.
- **Core Web Vitals**: field data by URL group, 28-day window; changes show 28 days after a fix.
- **Removals**: temporary hide (6 months); not a substitute for noindex or 404.
- **Settings → Search generative AI control**: opt-out from AI features; owner decision only.
- **Links**: top linked pages and linking sites; enough for a first backlink sanity check.

## Analytics: organic without lying

- GA4 default channel "Organic Search" includes Google, Bing, DuckDuckGo, Ecosia. Split by
  `session_source` when Bing matters.
- Consent Mode v2 (EU): without consent GA4 records modelled or no data; organic numbers are
  a lower bound. State this in every report. Server-side privacy-first analytics (Plausible,
  Umami, Matomo) count more completely but without user-level attribution.
- AI referrals: `chatgpt.com`, `perplexity.ai`, `claude.ai`, `copilot.microsoft.com`,
  `gemini.google.com`, `you.com`. Build one "AI assistants" channel group. Google AI Mode and
  AI Overview clicks arrive as `google / organic`; they cannot be separated in GA4.
- Landing page × conversion is the report that matters. Traffic without a conversion metric
  is a vanity number.

## Branded vs non-branded

Search Console Performance → Queries → filter "Query does not contain: brand" (regex for
variants: `(?i)wythropic|wythropic\.de|wytropic`). Brand queries measure marketing and
reputation; non-brand measures SEO. Report both, never blended.

## Traffic-drop diagnosis, in order

Do not skip steps; each rules out a class of causes.

1. **Verify the drop is real**: Search Console vs analytics, same period, same metric. A
   tracking or consent change produces analytics drops with stable Search Console clicks.
2. **Date and shape**: cliff (technical, manual action, redirect) vs slope (algorithmic,
   competition, seasonality). Compare year over year for seasonality.
3. **Impressions or CTR?** Impressions down = ranking or indexing. CTR down with stable
   impressions = SERP layout change (AI Overview, new feature, title rewrite) or a snippet
   problem.
4. **All pages or a segment?** Site-wide = technical, manual action, core update. One
   directory or template = a template bug, a canonical change, thin content judged as a group.
5. **Search Console → Manual actions / Security issues.** If present, that is the cause.
6. **Deployment history**: new `noindex`, robots.txt change, URL migration, canonical to
   staging, CDN rule, consent wall, framework upgrade with streaming metadata. `git log` on the
   head/layout/robots/sitemap files around the date. Run `crawl_check.py` and `seo_check.py`.
7. **Google update?** Check the ranking updates history against the date. Core update = content
   portfolio review, no quick fix; spam update = policies review.
8. **Competition and SERP**: who took the positions, with what. Fan-out citations in AI
   Overviews shift clicks even when rankings hold.
9. **Seasonality and demand**: Google Trends for the head terms.

Write the diagnosis as: date, affected segment, metric that moved, evidence, cause, fix,
verification method. Not as a list of guesses.

## Monitoring cadence

| Interval | Check |
|---|---|
| Every deploy | `seo_check.py dist/ --base-url … --fail-on error`; `crawl_check.py origin --limit 50` |
| Weekly | Search Console Pages report for new exclusions; Performance week-over-week; Enhancements errors |
| Monthly | Non-brand clicks and conversions by landing page; CWV field status; Business Profile performance; Bing index count |
| Quarterly | Bottom 20% of pages: refresh, consolidate or prune; backlink sanity; re-run keyword gap |
| After every Google update | Top 20 pages by clicks: position, CTR, content check against the core test |

## Reporting rules

- Every number carries its source and period. "Clicks +23% (GSC, 28 days vs previous 28 days)".
- Impressions in AI features are reach, not traffic. Do not report them as clicks.
- No "AI visibility score", "AI share of voice" or "position in AI Overview" claims. Not measurable.
- Lower bounds from consent-gated analytics are stated as such.
- A ranking change on a query with 10 impressions is noise. Aggregate.
- Estimated effort next to every recommendation, and the verification method that proves it worked.

## Sources

- Search Console help centre: https://support.google.com/webmasters
- Performance report: https://support.google.com/webmasters/answer/7576553
- Generative AI performance report: https://support.google.com/webmasters/answer/16984139
- Page indexing report: https://support.google.com/webmasters/answer/7440203
- URL Inspection: https://support.google.com/webmasters/answer/9012289
- Core Web Vitals report: https://support.google.com/webmasters/answer/9205520
- Debugging drops in Search traffic: https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops
- Ranking updates history: https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history
- GA4 default channel groups: https://support.google.com/analytics/answer/9756891
- Consent Mode: https://support.google.com/analytics/answer/9976101
- Bing Webmaster Tools: https://www.bing.com/webmasters
