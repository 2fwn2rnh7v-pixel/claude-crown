# Content Quality, E-E-A-T and Spam Policies

## Contents
- The core test
- Non-commodity content
- E-E-A-T in concrete page elements
- Title, meta description, headings
- Keyword work without keyword stuffing
- Spam policies you violate by accident
- AI-generated content
- Content lifecycle: refresh, consolidate, prune
- Per-page assessment grid
- Sources

---

## The core test

Google does not describe quality via formatting rules but via user satisfaction: would a
visitor leave the page feeling their task is done, without needing to search again? If yes,
the direction is right.

Three questions per page:

1. **Originality**: does the page contain information, data, measurements, screenshots or
   judgements that do not exist elsewhere in this form?
2. **Competence**: is it visible who wrote this and why that person can judge it?
3. **Purpose**: is the page built for readers or primarily for search engines?

## Non-commodity content

Google's AI-features guide (updated 2026-07-10) uses the term explicitly:

- **Commodity**: "7 tips for first-time buyers". General knowledge, interchangeable, producible
  by anyone, including a language model.
- **Non-commodity**: "Why we skipped the viewing and what the sewer inspection found". Own
  experience, concrete numbers, verifiable details.

For a SaaS or professional app: feature pages that only describe what the product does are
commodity. Pages that show which problem was solved at which company size with which
numbers are not. For a studio or agency: a real, interactive demo beats a description of a
demo; a case with before/after metrics beats a service list.

First-person evidence that counts: own screenshots instead of stock images, real
measurements, customer quotes with context, documented failed attempts, comparison tables
with self-tested alternatives, dates.

## E-E-A-T in concrete page elements

E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) is not a score but a
bundle of signals that quality raters evaluate and ranking systems approximate. Make it
visible:

| Signal | Implementation on the page |
|---|---|
| Experience | First-person perspective with evidence: "We accompanied 40 farms over two seasons…"; at least one proof the author has done the thing |
| Expertise | Author box with role, qualification, link to author page, `Person` schema, `ProfilePage` on the author page |
| Authoritativeness | Linked sources, third-party quotes, press/trade articles, case studies, consistent entity data (same name, address, socials everywhere) |
| Trustworthiness | Impressum, contact, address, transparent prices, HTTPS, privacy policy, date of last update, real reviews |

For YMYL topics (money, health, law, safety, and since 2025 civics/elections) missing author
and operator information is a hard defect, not a detail. The Quality Rater Guidelines
(September 2025 version) rate content with no visible effort, originality or added value as
Lowest, and explicitly include AI-generated content in that definition. Credentials claimed on
an About page must be verifiable elsewhere (register entry, LinkedIn, publications, press);
unverifiable claims add nothing and read as a trust defect.

## Title, meta description, headings

**`<title>`**
- Unique per page, primary search goal first
- About 50–60 characters visible; Google rewrites titles when it sees fit (roughly 60% of
  the time in third-party studies), mostly when titles are too long, keyword-stacked or
  identical across pages
- Pattern: `Primary topic – benefit | Brand`. For the homepage `Brand – what it is, for whom`
- Title and H1 may differ but must describe the same page
- German: umlauts count as one character, but `ß`, `ä` render wider; check pixel width when
  near the limit

**`<meta name="description">`**
- Not a ranking factor, a CTR factor
- About 120–160 characters, states concretely what the page delivers, ideally with a number,
  a place or a price
- Individual per page; if missing, Google generates a snippet from the text (often fine for
  long-form, bad for landing pages)

**Headings**
- Exactly one `<h1>` that names the page topic
- Hierarchy without skips (h1 → h2 → h3), no headings for visual effect
- Headings structure the text, they do not place keywords. Question headings are fine when
  the paragraph beneath actually answers the question in the first sentence.

## Keyword work without keyword stuffing

What works:
- Use the words users actually use, in prominent places (title, H1, anchor texts, alt texts,
  first paragraph)
- Match search intent: informational / navigational / transactional / commercial
  investigation. One page per intent, not one page per keyword variant
- Bundle topics instead of multiplying variants. Method in `keyword-intent.md`

What does not work:
- Keyword density as a target
- One landing page per city/adjective combination
- Hidden text, text in background colour, bloated lists

Google understands synonyms and semantic relations; an exact word match is not required.

## Spam policies you violate by accident

Google's spam policies (updated 2026-08-28) list: cloaking, doorway abuse, expired domain
abuse, hacked content, hidden text and links, keyword stuffing, link spam, machine-generated
traffic, malicious practices, misleading functionality, scaled content abuse, scraping, site
reputation abuse, sneaky redirects, thin affiliation, user-generated spam, policy circumvention,
scam and fraud.

| Policy | Typical unintended case |
|---|---|
| Scaled content abuse | Programmatically generated pages for every keyword combination, with or without AI |
| Doorway abuse | Near-identical city/industry landing pages all leading to the same form |
| Site reputation abuse | Third-party content (coupons, gambling, reviews) on your domain to ride its authority |
| Expired domain abuse | Buying an expired domain to host unrelated content for its old links |
| Cloaking | Different content for bots than for users, often accidental via user-agent branches or consent walls |
| Sneaky redirects | JS redirect that only fires for certain referrers or devices |
| Hidden text | Text blocks hidden for layout reasons, full of keywords |
| Link spam | Bought links, mass directories, footer link exchange, unmarked sponsored links (use `rel="sponsored"`) |

Violations lead to ranking demotion or a manual action (visible in Search Console).
Spam updates in 2025–2026: 2025-08-26, 2026-03-24, 2026-06-24, 2026-08-18.

## AI-generated content

Google's position: the production method is irrelevant, the intent counts. AI-assisted content
is allowed when it is checked, factually correct and useful for people. Mass production
without human review to manipulate rankings falls under scaled content abuse. Quality raters
are told to rate AI-summarised content with no added value and no human author attribution
as Lowest regardless of accuracy.

Working rule: AI may structure, draft and research. Every published page needs a named human
responsible, checked facts and at least one element only this team can provide (own data,
own photos, own position, own case).

## Content lifecycle: refresh, consolidate, prune

Core updates (2025: March, June, December; 2026: March, May) reward sites whose pages hold up
on the core test and demote pages that do not. No quick fix exists; the lever is the content
portfolio.

- **Refresh** when the topic still has demand but the page lost position: update facts,
  dates, screenshots, add what competitors now cover, keep the URL, set `dateModified` only
  when substance changed.
- **Consolidate** when several thin pages serve one intent: merge into the strongest URL,
  301 the others, update internal links and sitemap.
- **Prune** when a page has no demand, no links and no purpose: 410/404 it. `noindex` only
  when the page must stay reachable for users (account pages, thank-you pages).
- Never delete pages with backlinks without a 301 to the closest equivalent.
- Cadence: review the bottom 20% of pages by clicks every quarter; review the top 20 pages
  every core update.

## Per-page assessment grid

Document every audited page in this form:

```
URL: /leistungen/bodenanalyse
Intent: transactional (request a quote)
Meets intent: partly. Price missing, CTA after 1200 words
Originality: weak. No own data, interchangeable text
E-E-A-T: no author, no date, Impressum present
Title: "Bodenanalyse" (too generic, no benefit)
H1: missing (only h2)
Recommendation: add price range, case with measurements, author box, rewrite title
```

## Sources

- Helpful, reliable, people-first content: https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Spam policies (updated 2026-08-28): https://developers.google.com/search/docs/essentials/spam-policies
- AI-generated content: https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- Title links: https://developers.google.com/search/docs/appearance/title-link
- Snippets/descriptions: https://developers.google.com/search/docs/appearance/snippet
- Core updates: https://developers.google.com/search/docs/appearance/core-updates
- Ranking updates history: https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history
- Search Quality Rater Guidelines (PDF): https://guidelines.raterhub.com/searchqualityevaluatorguidelines.pdf
- Evaluating third-party SEO advice: https://developers.google.com/search/docs/fundamentals/third-party-seo
- Qualifying outbound links (`sponsored`, `ugc`, `nofollow`): https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links
