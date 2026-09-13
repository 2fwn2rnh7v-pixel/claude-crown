# Structured Data (JSON-LD)

## Contents
- Ground rules
- What Google still renders (status 2026-09)
- Retired rich results
- Choosing a type
- Templates
- Policy violations
- Validation
- Sources

---

## Ground rules

- Format: **JSON-LD** in `<script type="application/ld+json">`, in `<head>` or `<body>`.
  Microdata and RDFa work but are harder to maintain.
- Mark up only what is **visible** to users on the page.
- Use only types for which Google renders a rich result. Anything else has no effect in
  Search (it can still serve other consumers, e.g. knowledge graphs, agents).
- Structured data is **not required** for AI Overviews or AI Mode. Google says so explicitly.
  It is a path to rich results, not a ranking booster.
- When injected via JavaScript, make sure it ends up in the rendered DOM; better: render it
  server-side.
- Keep `@id` values stable and link entities (`publisher`, `author`, `isPartOf`) instead of
  marking every page in isolation. One `Organization` node with `@id: https://domain.tld/#organization`,
  referenced everywhere.
- One JSON-LD block per page with `@graph` is fine; several blocks are fine too.

## What Google still renders (status 2026-09)

Search gallery (updated 2026-06-15): Article, Breadcrumb, Carousel, Course list, Dataset,
Discussion forum, Education Q&A, Employer aggregate rating, Event, Image metadata, Job
posting, Local business, Math solver, Movie, Organization, Product (incl. merchant listings,
variants, shipping and return policies), Profile page, Q&A, Recipe, Review snippet, Software
app, Speakable, Subscription and paywalled content, Vacation rental, Video.

Copy the templates from `assets/jsonld/` and fill them from real page data. Never invent
ratings, prices, dates or people.

## Retired rich results

| Type | Status |
|---|---|
| `FAQPage` | Rich result **removed from Search on 2026-05-07**, documentation deleted June 2026. Markup is harmless, effect is zero. |
| `HowTo` | Removed September 2023. |
| Sitelinks search box (`WebSite` + `SearchAction`) | Removed November 2024. |
| Course info, Claim review (fact check), Estimated salary, Learning video, Special announcement, Vehicle listing, Practice problems | Announced June 2025, no longer shown since, Search Console reports removed January 2026. |
| Book actions | Announced for removal 2025, reversed November 2025, still supported. |

Google's stated reason: rarely used features that added little. Ranking is unaffected.
`seo_check.py` flags these as `JSONLD_RETIRED` (info). Remove them only if they cost
maintenance; otherwise ignore.

## Choosing a type

| Page type | Schema | Rich result |
|---|---|---|
| Homepage / about | `Organization` (+ `sameAs`, `logo`, `contactPoint`) | Knowledge panel signals, site name, logo |
| Every sub-page | `BreadcrumbList` | Breadcrumb path in the SERP |
| Blog / trade article | `Article` / `BlogPosting` / `NewsArticle` | Article display, author, date |
| Product / price page (e-commerce) | `Product` + `Offer` (+ `shippingDetails`, `hasMerchantReturnPolicy`) | Price, availability, ratings |
| SaaS / app | `SoftwareApplication` | App details, price |
| Service with a location | `LocalBusiness` (or a subtype: `Restaurant`, `RealEstateAgent`, `BeautySalon`) | Local results, hours |
| Recipe, job, event, course list | `Recipe`, `JobPosting`, `Event`, `Course` (list) | Own rich result each |
| Author page | `ProfilePage` + `Person` | Author context, E-E-A-T |
| Video page | `VideoObject` | Video result, key moments |
| Forum / community thread | `DiscussionForumPosting` | Forum result |

Pages about a service without a location (consulting, web design delivered remotely) get
`Organization` on the homepage and `Service` on the service page. `Service` has no rich
result; it still helps entity understanding and costs nothing.

## Templates

Full, copy-ready files in `assets/jsonld/`. Minimal shapes:

**Organization (once, homepage or layout)**

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://domain.tld/#organization",
  "name": "Company name",
  "url": "https://domain.tld",
  "logo": "https://domain.tld/logo.png",
  "sameAs": ["https://www.linkedin.com/company/…", "https://www.instagram.com/…"],
  "contactPoint": { "@type": "ContactPoint", "contactType": "customer support", "email": "hallo@domain.tld" }
}
```

**BreadcrumbList (per sub-page)**

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Start", "item": "https://domain.tld/" },
    { "@type": "ListItem", "position": 2, "name": "Leistungen", "item": "https://domain.tld/leistungen" },
    { "@type": "ListItem", "position": 3, "name": "Bodenanalyse" }
  ]
}
```

The last element deliberately has no `item`.

**Article**

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Title, max 110 characters",
  "image": ["https://domain.tld/bild-16x9.jpg"],
  "datePublished": "2026-03-01T09:00:00+01:00",
  "dateModified": "2026-06-12T14:30:00+02:00",
  "author": { "@type": "Person", "name": "First Last", "url": "https://domain.tld/team/first-last" },
  "publisher": { "@id": "https://domain.tld/#organization" }
}
```

Set `dateModified` only when the content really changed.

**LocalBusiness** (see `assets/jsonld/localbusiness.json` for the full field set):
`name`, `address` (PostalAddress), `geo`, `telephone`, `openingHoursSpecification`, `url`,
`image`, `priceRange`, `sameAs` (Google Business Profile, social). NAP must match the Google
Business Profile and the Impressum character for character.

## Policy violations

- Markup for content that does not exist on the page
- Self-assigned `aggregateRating` without real, visible user reviews
- `Review` markup for your own company on your own site
- Wrong type to force a rich result (e.g. `Recipe` for a guide)
- Prices or availability in markup that differ from what is displayed
- `Organization` markup claiming credentials or awards not shown anywhere else

Consequence: loss of rich results for the domain or a manual action (structured data spam).

## Validation

1. `seo_check.py`: JSON parse errors, type inventory, retired types, rating markup present.
2. Rich Results Test: https://search.google.com/test/rich-results — shows what Google actually
   recognises, after rendering.
3. Schema Markup Validator: https://validator.schema.org — syntax against schema.org.
4. Search Console → "Enhancements": errors on live URLs over time.

Order in an audit: script first, then the critical templates in the Rich Results Test.

## Sources

- Introduction: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- General policies: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- Feature gallery (updated 2026-06-15): https://developers.google.com/search/docs/appearance/structured-data/search-gallery
- Simplifying the results page (2025-06) and update (2025-11): https://developers.google.com/search/blog/2025/06/simplifying-search-results, https://developers.google.com/search/blog/2025/11/update-on-our-efforts
- Article: https://developers.google.com/search/docs/appearance/structured-data/article
- Organization: https://developers.google.com/search/docs/appearance/structured-data/organization
- Local business: https://developers.google.com/search/docs/appearance/structured-data/local-business
- Breadcrumb: https://developers.google.com/search/docs/appearance/structured-data/breadcrumb
- Product: https://developers.google.com/search/docs/appearance/structured-data/product
- Profile page: https://developers.google.com/search/docs/appearance/structured-data/profile-page
- Schema.org: https://schema.org
