# New Page Launch Checklist

Run for every new public page (landing page, service page, article) before it goes live.
Copy into the task and tick.

```
SEO launch: [URL]
- [ ] Intent named (informational / commercial / transactional) and primary query chosen
- [ ] Rendered server-side: `curl -sL URL | grep -i "<h1"` shows the H1
- [ ] Exactly one <h1> naming the topic; h2/h3 without skips
- [ ] <title> 15–60 chars, unique, search goal first, brand last
- [ ] <meta name="description"> 70–160 chars, concrete (number, place, price)
- [ ] Self-referencing absolute canonical to the production host
- [ ] <html lang="de"> (or correct language), viewport meta present
- [ ] Open Graph: og:title, og:description, og:url = canonical, og:image 1200×630 absolute
- [ ] Images: alt text, width/height, WebP/AVIF, LCP image fetchpriority="high" and not lazy
- [ ] Internal links: linked from at least one hub/nav page; page links onward (real <a href>)
- [ ] JSON-LD: BreadcrumbList; page type (Article / Service / LocalBusiness / Product); no invented ratings
- [ ] No noindex, not blocked in robots.txt, listed in sitemap with real lastmod
- [ ] Contains at least one non-commodity element (own data, case, photo, position, date)
- [ ] Author/operator visible where the topic is YMYL; Impressum linked
- [ ] Consent banner reserves space; no content hidden behind it
- [ ] `seo_check.py <file|URL> --base-url https://… --fail-on error` exit 0
- [ ] After deploy: Search Console URL Inspection → request indexing; Bing IndexNow ping
```
