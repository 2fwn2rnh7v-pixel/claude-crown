# Technical SEO

## Contents
- Minimum technical requirements
- Controlling crawling (robots.txt)
- Controlling indexing (noindex, canonical)
- Status codes and redirects
- Sitemaps
- Rendering and JavaScript
- CDN, WAF and bot protection
- Internal linking and URL structure
- Internationalisation (hreflang)
- Core Web Vitals
- Images and video
- Bing and other engines
- Sources

---

## Minimum technical requirements

For a page to appear in Google at all, three things must hold:

1. Googlebot is not blocked (robots.txt, firewall, bot protection, geo-blocking).
2. The page answers HTTP 200 and returns indexable content.
3. The page carries no `noindex`.

Everything else is optimisation, not a prerequisite. Meeting the requirements does not
guarantee indexing. Google decides freely about crawling, indexing and serving.

Verify with `scripts/crawl_check.py <origin>` (robots, sitemap, status, soft-404, bot view)
before touching a single meta tag.

## Controlling crawling (robots.txt)

- Must live at `https://domain.tld/robots.txt`. Served with 200. A 5xx makes Google pause
  crawling the whole host; a 404 means "everything allowed".
- `Disallow` prevents **crawling**, not indexing. A URL blocked in robots.txt can still
  appear as a result (without snippet) if it is linked strongly. To keep a page out of the
  index use `noindex`, and for that the page must be crawlable. `Disallow` + `noindex` at
  the same time is a mistake: Google never sees the noindex.
- Never block CSS and JS. Without them Google cannot render the page or judge mobile
  friendliness.
- Typical minimal case for an app with a private area:

```
User-agent: *
Disallow: /api/
Disallow: /app/
Disallow: /admin/
Allow: /

Sitemap: https://domain.tld/sitemap.xml
```

- AI crawler rules are a separate, deliberate decision. See `ai-search.md`. They do not
  affect Google Search rankings.

## Controlling indexing

**noindex** per page:

```html
<meta name="robots" content="noindex, follow">
```

or as a header for non-HTML resources: `X-Robots-Tag: noindex`.

**Canonical**: self-referencing and absolute on every indexable page:

```html
<link rel="canonical" href="https://domain.tld/preise">
```

Frequent mistakes:
- Canonical points to `localhost`, a staging or preview host (`*.vercel.app`, `*.pages.dev`,
  `*.workers.dev`) or the homepage. Build-time bug, production-level damage.
- Two canonical tags (layout plus page). Google ignores both.
- Canonical and `sitemap.xml` disagree (`/preise/` vs `/preise`).
- Paginated lists canonicalise to page 1, so detail pages only linked from page 2+ vanish.
- Parameter URLs (`?utm_source=`, `?sort=`) without canonical to the clean variant.
- `noindex` plus canonical on the same page: contradictory signals, Google picks one.

**Duplicate content** is not a penalty, but it burns crawl budget and splits signals
across URLs. Reduce, do not ignore.

## Status codes and redirects

| Situation | Correct |
|---|---|
| Page moved permanently | 301 (or 308) |
| Temporarily elsewhere | 302 / 307 |
| Page deleted, no replacement | 404 or 410 |
| Deleted, but server answers 200 with "not found" text | **Soft 404, error** |
| Maintenance | 503 with `Retry-After` |

- Collapse redirect chains (`A → B → C`). Each hop costs crawl budget; Google follows up
  to 10 hops, users and third-party crawlers fewer.
- Redirects belong in server or host config, never in JavaScript or `<meta http-equiv="refresh">`.
- `http → https → www` must settle in **one** hop from each entry point.
- SPA hosting defaults produce soft 404s: Cloudflare Workers static assets with
  `not_found_handling = "single-page-application"` serve `index.html` with **200** for every
  unknown path. Use `"404-page"` with a real `404.html`, or handle the route in the Worker and
  return status 404. Same pattern on Netlify (`/* /index.html 200`) and Vercel rewrites.
  `crawl_check.py` probes this (`SOFT_404`).

## Sitemaps

- Only canonical, indexable 200 URLs. No `noindex`, no redirects, nothing blocked by robots.txt.
- Max 50,000 URLs or 50 MB uncompressed per file; above that use a sitemap index.
- `<lastmod>` only with the real change date, in W3C datetime format. If every URL carries
  the same or a daily-bumped `lastmod`, Google stops trusting the field for that site.
  `<priority>` and `<changefreq>` are ignored by Google.
- Declare the sitemap in robots.txt and submit it in Search Console. Then read the
  "Pages" (indexing) report for exclusion reasons, not the submission success message.
- Image and video sitemap extensions still work; use them when media is the product.
- Google does **not** support IndexNow. Bing, Yandex, Naver, Seznam and Yep do. Ping
  IndexNow anyway when Bing visibility matters (it feeds ChatGPT search and Copilot).

## Rendering and JavaScript

Google renders JavaScript with an evergreen Chromium, but in a second, deferred wave and
with a limited budget. Practical rules:

- Ranking-relevant content (main text, H1, links, meta tags) should be in the **initial
  HTML**: SSR, SSG or ISR instead of pure client rendering.
- Test without JS: `curl -sL https://domain.tld/path | grep -i "<h1"`. Nothing there is a
  blocker. Then compare with Search Console URL Inspection → "View crawled page" → HTML.
- Navigation via `<a href="…">`. A `<div onClick={router.push()}>` is not a link for crawlers.
  Framework `<Link>` components render real anchors; custom click handlers often do not.
- Lazy loading: content that only loads on scroll or click is normally invisible to Google.
  `loading="lazy"` on images is fine, except on the LCP image.
- Hash routing (`/#/preise`) is one URL for Google. Use the History API with server support.
- Shadow DOM content is rendered; content in closed iframes or behind consent walls is not.
- Soft 404 in SPAs: client-rendered "not found" states answer HTTP 200. Return a real 404
  server-side; in Next.js call `notFound()`, in TanStack Start throw `notFound()` from the
  loader and set the status in the root `notFoundComponent` response.
- **Streaming metadata (Next.js ≥ 15.2):** for JS-capable bots, metadata from
  `generateMetadata` is appended to `<body>` after the initial flush. Google reads it. HTML-
  limited bots (`facebookexternalhit`, many SEO tools, `curl`) get a blocking render with
  metadata in `<head>`. Audit with both user agents; `seo_check.py --user-agent facebookexternalhit`.

## CDN, WAF and bot protection

The most expensive invisible failure: robots.txt allows, the edge blocks.

- Cloudflare blocks AI crawlers **by default** for new zones since July 2025 and, from
  2026-09-15, blocks "mixed-use" crawlers (training + search in one UA) on ad-carrying pages
  for new zones and free plans. Googlebot is mixed-use by Cloudflare's definition. Check
  Security → Bots → AI crawlers and Verified Bots after every zone change.
- Bot Fight Mode, "Under Attack" mode, rate limits and country blocks regularly hit
  Googlebot (US IPs) and `Google-InspectionTool`. Verify with Search Console URL Inspection
  → Live Test, and with server logs grouped by user agent and status.
- Rules must agree on three layers: robots.txt, CDN/WAF, origin. Test each separately.
- `crawl_check.py` compares a browser UA with an HTML-limited bot UA (`BOT_VIEW_DIFFERS`).
  A 403/429/503 for the bot while the browser gets 200 is an edge block.

## Internal linking and URL structure

- Readable, lowercase URLs with hyphens: `/leistungen/bodenanalyse`, not `/p?id=8842`.
  Umlauts: prefer transliteration (`ae`, `oe`, `ue`, `ss`); if using IDN/UTF-8 paths, be
  consistent and percent-encode in sitemaps and canonicals.
- Flat hierarchy: important pages within 3 clicks of the homepage.
- Anchor text describes the target ("Preise für Bodenanalysen"), not "click here".
- Find orphan pages (only in the sitemap, linked nowhere) and link them from a hub.
- Change URLs only with 301 and a simultaneous update of canonical, sitemap and internal links.
- One hub page per topic cluster, spokes link up to the hub and sideways to siblings.

## Internationalisation (hreflang)

```html
<link rel="alternate" hreflang="de-DE" href="https://domain.tld/de/preise">
<link rel="alternate" hreflang="de-AT" href="https://domain.tld/at/preise">
<link rel="alternate" hreflang="de-CH" href="https://domain.tld/ch/preise">
<link rel="alternate" hreflang="x-default" href="https://domain.tld/preise">
```

Rules: every variant lists all others **including itself**; language codes ISO 639-1,
regions ISO 3166-1 alpha-2; absolute URLs; `x-default` for the fallback. Alternatively via
HTTP header or sitemap (`xhtml:link`). Mixing methods on one site invites inconsistencies.
hreflang is a hint for serving the right variant, not a ranking signal; each variant still
needs its own indexable, non-duplicate content. `de-DE` / `de-AT` / `de-CH` pages that differ
only in currency and a phone number are treated as duplicates.

## Core Web Vitals

Targets, measured at the 75th percentile of real users (field data):

| Metric | Good | Needs improvement | Poor |
|---|---|---|---|
| LCP (Largest Contentful Paint) | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s |
| INP (Interaction to Next Paint) | ≤ 200 ms | 200–500 ms | > 500 ms |
| CLS (Cumulative Layout Shift) | ≤ 0.1 | 0.1–0.25 | > 0.25 |

INP replaced FID in March 2024. Google (doc updated 2025-12-10): good CWV "aligns with what
our core ranking systems seek to reward". A tie-breaker among comparable pages, not a lever
that outranks relevance.

Typical causes and remedies:

**LCP** (break it down: TTFB → resource load delay → resource load time → render delay)
- Hero image without priority → `fetchpriority="high"` (Next.js `priority`), never `loading="lazy"`
- Hero image discovered late (CSS background, JS-injected) → put it in HTML, `<link rel="preload" as="image">`
- Render-blocking CSS/JS → critical CSS inline, rest deferred
- Web fonts → `font-display: swap`, preload the display face, subset to `latin`
- Slow TTFB → caching, CDN, ISR/SSG instead of SSR per request

**INP**
- Long tasks on the main thread → code splitting, heavy work in `requestIdleCallback` or a
  Worker, `startTransition` for React state updates; find them with the Long Animation
  Frames API (LoAF) in DevTools Performance panel
- Large hydration bundles → fewer client components, server components
- Third-party scripts (chat, analytics, consent) → load deferred, facades for embeds

**CLS**
- Images/videos without `width`/`height` or `aspect-ratio`
- Late-inserted banners, cookie layers, ads → reserve the space
- Font swap without `size-adjust` → match fallback metrics

**Speculation Rules API** (`<script type="speculationrules">`, Chrome): prerender likely next
pages for near-instant navigations. Improves LCP on the second page view, not the first.
Exclude pages with side effects and analytics double counting.

Measure: PageSpeed Insights (field + lab), `web-vitals` library for own RUM, Search Console
"Core Web Vitals" report (field, per URL group). A good Lighthouse score with poor field data
is not a success.

## Images and video

- `alt` describes the content for someone who cannot see it; decorative images get `alt=""`.
- Descriptive file names: `bodenanalyse-probenahme.webp`, not `IMG_4821.jpg`.
- AVIF/WebP, responsive `srcset` + `sizes`, dimensions set, 2× display size maximum.
- Images in `<img>` (or `<picture>`), not CSS backgrounds, if they should rank in Google Images.
- Open Graph image 1200×630, absolute URL, under 1 MB. `twitter:card` is optional; X falls
  back to OG tags.
- Video: `VideoObject` markup with `thumbnailUrl`, `uploadDate`, `contentUrl` or `embedUrl`;
  self-hosted video needs a video sitemap or markup to be discovered at all. YouTube embeds
  rank the YouTube URL, not the page.

## Bing and other engines

Bing's index feeds Bing, Microsoft Copilot, DuckDuckGo, Yahoo and, as of 2026, ChatGPT
search retrieval. For German-speaking markets Bing's share is small, but AI-answer reach is
not. Minimum: verify the site in Bing Webmaster Tools (import from Search Console), submit
the sitemap, enable IndexNow. Bing renders JS less reliably than Google; SSR matters more there.

## Sources

- Search Essentials: https://developers.google.com/search/docs/essentials
- Technical requirements: https://developers.google.com/search/docs/essentials/technical
- SEO Starter Guide: https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- robots.txt: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- Canonicalisation: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- Sitemaps: https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
- JavaScript SEO: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- hreflang: https://developers.google.com/search/docs/specialty/international/localized-versions
- Core Web Vitals (Google Search, updated 2025-12-10): https://developers.google.com/search/docs/appearance/core-web-vitals
- web.dev Vitals: https://web.dev/articles/vitals
- Speculation Rules: https://developer.chrome.com/docs/web-platform/prerender-pages
- Cloudflare static assets routing (SPA fallback 200): https://developers.cloudflare.com/workers/static-assets/routing/single-page-application/
- Cloudflare AI crawler default block (2025-07-01) and mixed-use rule (2026-09-15): https://blog.cloudflare.com/
- Next.js streaming metadata: https://nextjs.org/docs/app/api-reference/functions/generate-metadata#streaming-metadata
- Google Images: https://developers.google.com/search/docs/appearance/google-images
- Video: https://developers.google.com/search/docs/appearance/video
- IndexNow: https://www.indexnow.org/
- Debugging traffic drops: https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops
