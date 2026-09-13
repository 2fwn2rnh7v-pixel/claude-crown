---
name: seo-optimizer
description: >
  Audits, fixes and future-proofs website SEO against Google Search Essentials and 2026 AI
  search: crawling/indexing, rendering, titles, canonicals, hreflang, JSON-LD, Core Web Vitals,
  E-E-A-T, keyword intent, local SEO, AI crawlers, Search Console measurement. Ships two
  deterministic scripts (on-page check, crawl/sitemap/robots check), JSON-LD templates, report
  template, launch checklist and a lessons file; outputs prioritised findings with code patches.
  This skill should be used whenever a task involves SEO, rankings, Google, Bing, organic
  traffic, meta tags, sitemaps, robots.txt, canonical, Schema.org, rich results, PageSpeed,
  AI Overviews, AI Mode, ChatGPT/Perplexity citations, AEO, GEO, llms.txt, Google Business
  Profile, or when a landing, marketing, blog or location page is built. Also on vague asks
  like "why does nobody find us", "page does not rank", "traffic dropped", "are we AI-ready".
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/seo_check.py *), Bash(python ${CLAUDE_SKILL_DIR}/scripts/crawl_check.py *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/seo_check.py *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/crawl_check.py *)
metadata:
  version: 1.0.0
  source: built 2026-09-13 from a German seo-audit skill, extended with verified 2025–2026 Google documentation
---

# SEO Optimizer

Every finding in this skill is **reproducibly evidenced**: script output, rendered DOM, or a
file and line in the repo. No claims from the gut, no generic checklist sentences.

## Ground rules

1. **Measure first, then claim.** Before any statement about a page, obtain the rendered HTML
   (build output or `curl`), not the template source. SPA/SSR frameworks regularly differ.
2. **Eligibility before optimisation.** A page that cannot be crawled or indexed gains nothing
   from content work. Order: reachable → indexable → rendered → content → rich results → performance.
3. **No fix without a diff.** Deliver every recommendation as a concrete code change (file +
   patch), not prose advice.
4. **Google documentation beats blog opinion.** On conflict, Search Central wins. Mention
   third-party tools and "GEO hacks" only when they hold up against the official docs;
   otherwise list them under "Not relevant".
5. **Respect project copy rules.** Titles and descriptions are visible product copy: follow the
   project's language, register and style constraints (e.g. German UI text, no dashes) when
   writing them.

## Modes

| Mode | Trigger | Start with |
|---|---|---|
| **Audit** | "check SEO", "why not ranking", "traffic dropped" | Workflow below, full |
| **Fix** | findings exist, "fix it" | Steps 3 and 9; patch, re-run scripts until exit 0 |
| **Build** | new landing/marketing/blog/location page | `assets/page-launch-checklist.md`; verify with `seo_check.py` before declaring done |
| **Research** | "which keywords", "what should we write" | `references/keyword-intent.md`, output the cluster format |
| **AI visibility** | "AI Overviews", "ChatGPT", "llms.txt", "GEO" | `references/ai-search.md`; correct wrong premises before doing work |
| **Local** | shop, restaurant, studio, "in der Nähe", Google Business Profile | `references/local-seo.md` |

Read `references/lessons.md` at the start of every mode. Append to it after every correction.

## Workflow (Audit)

Copy this checklist into the response and keep it updated:

```
SEO audit progress:
- [ ] 1. Scope and stack
- [ ] 2. Obtain rendered HTML
- [ ] 3. Run seo_check.py (on-page) and crawl_check.py (robots/sitemap/status)
- [ ] 4. Crawl and index control (robots.txt, sitemap, canonical, status codes, CDN)
- [ ] 5. Content, intent and E-E-A-T
- [ ] 6. Structured data
- [ ] 7. Core Web Vitals
- [ ] 8. Findings report
- [ ] 9. Patch, re-run step 3, record the delta
```

### Step 1 — Scope and stack

Determine from the repo, not by asking, when derivable:

- Framework and rendering mode (SSG / SSR / ISR / client-only); hosting (Cloudflare, Vercel, Netlify)
- Where metadata is produced (`head()` in TanStack routes, Next `metadata`/`generateMetadata`,
  Astro layout, `<Helmet>`)
- Which routes should be indexable and which must not
- Language and country variants; local business or remote service

Framework patterns: `references/framework-recipes.md`.

### Step 2 — Obtain rendered HTML

Priority:

1. Production build output (`dist/`, `out/`, `.output/`, `.next/server/app/**/*.html`)
2. Local production server: `curl -sL http://localhost:3000/path`
3. Live URL; fetch twice, once as a browser and once as an HTML-limited bot
   (`seo_check.py URL --user-agent facebookexternalhit`)

If the page is empty without JavaScript, that is the first finding, not the meta description.

### Step 3 — Deterministic checks

```bash
python ${CLAUDE_SKILL_DIR}/scripts/seo_check.py dist/ --base-url https://domain.tld --json seo.json
python ${CLAUDE_SKILL_DIR}/scripts/crawl_check.py https://domain.tld --limit 100 --json crawl.json
```

- `seo_check.py`: files, directories or URLs. Title, description, H1, canonical (self-check via
  `--base-url`), noindex/nosnippet, meta refresh, lang, viewport, images, hreflang, Open Graph,
  JSON-LD validity and retired types, cross-page duplicates. `--fail-on warning` for a strict CI gate.
- `crawl_check.py`: live origin. robots.txt, sitemap (index-aware), per-URL status/redirect/
  noindex/canonical, soft-404 probe, redirect chain, browser-vs-bot view (detects CDN blocks).
- Both are stdlib-only; exit code 1 means at least one error. Codes are documented in each
  script's docstring (`--help`). Run them again after every fix until exit 0.
- They do **not** judge content quality. That is step 5.

### Step 4 — Crawl and index control

Details: `references/technical-seo.md`. Minimum:

- robots.txt blocks nothing that should be indexed; CSS/JS not blocked; 200, not 5xx
- `noindex` only on pages meant to stay out; never combined with `Disallow`
- One self-referencing absolute canonical per indexable page, production host
- Sitemap lists only indexable 200 canonicals, real `lastmod`
- 301/308 for permanent moves, real 404 for missing pages (SPA fallbacks answer 200)
- Every important page reachable via `<a href>`
- CDN/WAF does not block Googlebot or wanted AI crawlers (Cloudflare defaults changed 2025–2026)

### Step 5 — Content, intent and E-E-A-T

Grid in `references/content-quality.md`; intent method in `references/keyword-intent.md`.
Core question per page: **what is here that is not on ten other pages?**

Flag red:
- Commodity content without own data, experience or position
- Mass-generated page variants for keyword permutations (scaled content / doorway abuse)
- Missing author or operator information on money, health, legal topics
- Titles and H1s that do not name the search goal; page serving the wrong intent for its SERP

### Step 6 — Structured data

Patterns and policies: `references/structured-data.md`; copy-ready files in `assets/jsonld/`.
Rule: mark up only what users see, only types with a current Google rich result. `FAQPage` and
`HowTo` no longer produce one (2026-05 / 2023-09). Validate in the Rich Results Test afterwards.

### Step 7 — Core Web Vitals

Thresholds and causes: `references/technical-seo.md#core-web-vitals`. Field data (CrUX via
PageSpeed Insights, Search Console) beats lab data (Lighthouse). A good Lighthouse score with
poor field data is not a success.

### Step 8 — Findings report

Use `assets/report-template.md` exactly: Summary → Blockers → High → Medium → Content
assessment → Not relevant (deliberately dropped) → Verification → Next steps. Evidence is
concrete: `dist/preise/index.html:12 — <title> missing`, not "optimise titles". Report language
follows the user; code and identifiers stay English.

### Step 9 — Patch and re-measure

Implement fixes, re-run both scripts, record the before/after delta in the report. The
technical layer counts as done only at exit code 0. Then add any new lesson to
`references/lessons.md` (one line, symptom → rule).

## Frequent misjudgements this skill avoids

| Common assumption | Reality (source in references) |
|---|---|
| `llms.txt` improves AI-search visibility | Google does not read it; crawlers barely request it. Optional for dev docs, no ranking lever. |
| Content must be "chunked" for LLMs | Not needed; no ideal page length. |
| More pages = more visibility | Scaled page production for rankings is a spam policy violation. |
| Keyword density is a dial | No documented factor; synonyms are understood. |
| Schema.org is required for AI Overviews | No. Helps rich results, not a prerequisite for AI features. |
| `FAQPage` markup earns a rich result | Removed from Search 2026-05-07. |
| Blocking `Google-Extended` protects rankings or removes AI Overviews | It only controls Gemini training/grounding; no effect on Search. |
| A "position in AI Overviews" can be tracked | Not measurable. Search Console reports AI impressions only, no clicks or queries. |
| robots.txt allows, so crawlers get in | CDN/WAF defaults (Cloudflare 2025–2026) block independently; check logs. |
| Meta keywords / bought "mentions" help | Ineffective or spam risk. |

## Reference files

- `references/lessons.md` — symptom → rule lessons; read first, append after corrections
- `references/technical-seo.md` — crawling, indexing, rendering, status codes, CDN, hreflang, CWV, images, Bing
- `references/content-quality.md` — helpful content, E-E-A-T, spam policies, titles, lifecycle
- `references/keyword-intent.md` — intent taxonomy, free research sources, clustering, German market
- `references/structured-data.md` — what still renders, retired types, templates, policies
- `references/ai-search.md` — AI Overviews/AI Mode mechanics, AI crawlers, llms.txt, measurement
- `references/local-seo.md` — Google Business Profile, NAP, reviews policy, location pages
- `references/measurement.md` — Search Console reports, analytics, traffic-drop diagnosis, cadence
- `references/framework-recipes.md` — Next.js 16, TanStack Start, Astro, React Router 7, Vite, hosting

## Assets

- `assets/report-template.md`, `assets/page-launch-checklist.md`, `assets/robots.txt.example`
- `assets/jsonld/*.json` — Organization, LocalBusiness, BreadcrumbList, Article, Service, Product,
  SoftwareApplication, ProfilePage/Person, VideoObject
