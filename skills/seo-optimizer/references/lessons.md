# Lessons Learned

Field-tested rules. One line each: **symptom → rule**. Dated when the rule depends on a
change in Google or tooling. Read before every audit; append after every correction.

## How to append

- One bullet, max 20 words, pattern `symptom → rule`. Add `(YYYY-MM)` when time-bound.
- Check for an existing line first. Inaccurate line? Replace it, do not append a second.
- Only lessons that generalise beyond one site. Site-specific traps go into the project's own notes.
- Source or evidence in the line when the claim is not obvious (`per Google doc`, `seen in logs`).

## Process

- Audit started from `.tsx` sources → always fetch rendered HTML first; templates lie.
- Recommendations as prose → every finding needs file:line or URL and a diff.
- Report mixed blockers with nice-to-haves → order: reachable → indexable → rendered → content → rich results → performance.
- Claimed "fixed" without re-run → `seo_check.py` exit 0 and `crawl_check.py` exit 0 are the proof.
- Blog advice contradicts Search Central → Search Central wins; cite it.
- Client asks for an "AI visibility score" → not measurable; offer GSC Generative AI impressions instead.
- Good Lighthouse, bad CrUX → field data decides; lab is for debugging.
- Negative test passed (no errors found) → run a positive counter-test on a known-bad fixture first.

## Crawling and indexing

- Page in sitemap but excluded → check `noindex` first, then robots.txt, then canonical, then status.
- `Disallow` + `noindex` on the same URL → Google never sees the noindex; remove the disallow.
- robots.txt 5xx → Google pauses crawling the whole host; a 404 is safer than a broken file.
- Two canonicals (layout + page) → Google ignores both; one owner per tag.
- Canonical to `*.pages.dev` / `*.vercel.app` / `localhost` in production → build env leak; gate with `seo_check.py --fail-on error`.
- All `lastmod` identical or bumped daily → Google stops trusting lastmod for the site.
- Sitemap URL 307/301 → list the final URL; redirects in sitemaps waste crawl budget (seen live).
- `http → https → www` two hops → collapse to one from every entry.
- Random path answers 200 → SPA fallback; Cloudflare `not_found_handling: "single-page-application"` is a soft-404 machine (2026-09).
- Preview `X-Robots-Tag: noindex` shipped to production → most expensive single error; test headers, not just HTML.
- Paginated lists canonical to page 1 → detail pages only linked from page 2+ vanish.
- Staging blocked by password → fine; staging blocked only by robots.txt → gets indexed via links.

## Rendering and frameworks

- `curl` shows no `<h1>` → client-only rendering; blocker before any meta work.
- `<div onClick={navigate}>` → not a link for crawlers; use `<a href>` / framework `<Link>`.
- Hash routes `/#/preise` → one URL for Google; use History API with server routes.
- Next.js ≥ 15.2 meta tags appear in `<body>` → streaming metadata, not a bug; HTML-limited bots get blocking render (2026-09).
- TanStack Start missing `<HeadContent />` in root → no route `head()` output at all.
- Route `head()` sets `og:title` but not `title` → title falls back to root; set both.
- JSON-LD injected client-side → may miss the render; emit in `head().scripts` / server component.
- Consent wall hides main text until click → Googlebot never clicks; content invisible, possible cloaking.
- `notFound()` thrown in component, not loader → status still 200; throw in loader / set response status.
- Astro island holds the only text → static HTML empty; keep text outside islands.

## CDN and bot protection

- robots.txt allows, crawler still 403 → CDN/WAF; check Cloudflare Bots settings and logs by UA.
- Cloudflare new zone blocks AI crawlers by default (2025-07); mixed-use crawlers on ad pages from 2026-09-15 → verify Googlebot in URL Inspection Live Test.
- Rate limit hits Googlebot bursts → allow-list verified bots, not IP ranges.
- Country block on non-EU IPs → Googlebot crawls from US; blocking it blocks Google.

## Structured data

- `FAQPage` markup "for rich results" → removed from Search 2026-05-07; zero effect, harmless (per Google doc).
- `HowTo` markup → rich result gone since 2023-09.
- Sitelinks search box markup → retired 2024-11.
- Self-assigned `aggregateRating` → policy violation; only real, visible, first-party reviews.
- Markup for AI Overviews → not required (per Google, 2026-07); it is a rich-result tool.
- Price in markup ≠ price on page → merchant listing errors, possible manual action.
- Rich Results Test passes, Search Console shows errors → Search Console is the live truth; test the deployed URL.

## Content

- Page describes the product, nothing else → commodity; add own data, case, photos, position.
- Ten city pages, same text → doorway abuse; one page per real location.
- AI-drafted page published unreviewed → scaled content risk; named human owner, checked facts, one unique element.
- Title identical on many URLs → Google rewrites all; unique title with the search goal first.
- `<meta description>` missing on landing pages → Google picks random text; write it, it is CTR.
- Two `<h1>` (logo + headline) → headline is the h1; logo is `<a>` with image alt.
- Keyword density tuning → no documented factor; write for the intent.
- Fan-out citations from outside the top 10 (2026-02 studies) → cover sub-questions on the page, not one page per sub-question.

## AI search

- `llms.txt` proposed as SEO lever → Google does not read it (2025-07); "Not relevant" section, ship only for dev docs.
- Blocking `Google-Extended` to "protect content" → does not remove the site from Search or AI Overviews (per Google doc).
- Blocked `OAI-SearchBot` / `PerplexityBot` → invisible in ChatGPT search / Perplexity; decide deliberately.
- Site absent from Bing → absent from ChatGPT search and Copilot; verify in Bing Webmaster Tools, enable IndexNow.
- GSC Generative AI report shows impressions only (2026-08) → never report them as clicks.
- "Position in AI Overview" requested → not measurable; say so.

## Local

- Business name with keywords in profile → suspension risk; name as on signage.
- Incentivised reviews → forbidden by Google policy; ask, do not reward.
- NAP differs between site, profile, Impressum ("Str." vs "Straße") → pick one form everywhere.
- Service-area business lists 30 towns as pages → doorway; one page per service, areas inside.

## Performance

- Hero image `loading="lazy"` → LCP delay; `fetchpriority="high"`.
- LCP image only in CSS background → discovered late; put it in HTML or preload.
- Consent banner injected without reserved space → CLS; reserve height.
- Third-party chat/analytics in `<head>` → INP; defer or lazy-load.
- Font swap jumps → `size-adjust` on fallback, preload the display face.
- Fix shipped, CWV report unchanged → 28-day window; wait, verify in PSI field data.
