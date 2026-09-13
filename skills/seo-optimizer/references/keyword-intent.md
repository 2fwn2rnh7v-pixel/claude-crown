# Keyword and Intent Research

## Contents
- Why intent first
- Intent taxonomy
- Free sources, in order of trust
- Method: from seed to topic map
- Reading the SERP
- German market notes
- Paid tools, one line each
- Output format
- Sources

---

## Why intent first

A page ranks for the intent it satisfies, not for the words it contains. Google understands
synonyms and rewrites titles; it does not forgive a transactional page answering an
informational query or a thin page where the SERP shows 2,000-word guides. Research therefore
answers three questions per target: what do people want, what does Google already show for
it, and which single page on this site should own it.

## Intent taxonomy

| Intent | Signal words (DE/EN) | Page type that wins | Example |
|---|---|---|---|
| Informational | wie, was ist, warum, anleitung, how, guide | guide, explainer, FAQ-style section | "bodenanalyse wie oft" |
| Commercial investigation | beste, vergleich, test, erfahrungen, vs, alternative | comparison, review, case study | "bodenanalyse anbieter vergleich" |
| Transactional | kaufen, preis, kosten, angebot, buchen, termin, in der nähe | service/product page, local landing page | "bodenanalyse kosten" |
| Navigational | brand, product name, login | homepage, the named page | "agrarmonitor login" |

Mixed SERPs exist. When the top 10 split 50/50, pick the intent that matches the business
goal and make the page clearly that, with a link to the other.

## Free sources, in order of trust

1. **Search Console → Performance → Queries**, filtered by page. Real demand you already
   touch, including position 8–20 terms one rewrite away from page one. Export 16 months,
   compare.
2. **Google autocomplete** for the seed plus each letter a–z and each question word. Reflects
   real query logs.
3. **People also ask / Related searches** on the SERP: the fan-out questions Google itself
   associates. These are the sub-questions a page or cluster should answer.
4. **Google Trends**: seasonality and relative volume between two terms; no absolute numbers.
5. **Bing Webmaster Tools → Keyword Research**: absolute-ish volumes for free, Bing-skewed.
6. **Competitor pages**: which H2s do the top three share? That list is the table of contents
   Google expects.
7. **Sales and support inboxes**: the phrasing customers actually use, in their own words.
   Often the most valuable and the least used source.

## Method: from seed to topic map

1. **Seeds**: 5–15 terms from the offer (`Angebot`), one per service or product.
2. **Expand** each seed via autocomplete, PAA, related searches, GSC queries. Keep the raw list.
3. **Classify** every query by intent (table above). Drop navigational for other brands.
4. **Cluster** by shared SERP: two queries belong to one page when the top 10 overlap by at
   least 4–5 URLs. Without a tool, spot-check the top 5 manually; same results = same page.
5. **One page per cluster.** Name the primary query (highest demand, clearest intent), list
   the secondary queries that the page must also answer in H2s or paragraphs.
6. **Hub and spokes**: the service page is the hub; guides and cases are spokes linking up.
   Each spoke targets one informational or commercial cluster.
7. **Gap check**: clusters with no page → content plan; pages with no cluster → candidates for
   consolidation or pruning.
8. **Priority** = demand × intent fit × current position. A position-12 transactional term
   beats a position-40 informational term every time.

## Reading the SERP

Before writing, open the SERP for the primary query and note:

- Dominant page type in the top 5 (guide, product, list, local pack, video)
- SERP features: AI Overview, local pack, shopping, video, PAA, sitelinks, images
- Word count and structure of the top 3 (headings, tables, FAQs)
- Freshness: are results from the last 12 months?
- Brand share: are positions 1–5 all big brands or directories? Then the realistic target is
  the fan-out sub-query, the local variant or a commercial comparison, not the head term.
- If an AI Overview is present, which pages it cites and what they have that others lack
  (data, first person, a table). That is the bar.

## German market notes

- Compound nouns: "Bodenanalysekosten" and "Bodenanalyse Kosten" are the same intent;
  Google handles it. Write the natural form, not both.
- Umlauts: users type both "Düngung" and "Duengung"; Google normalises. URLs: transliterate.
- Regional variants: DE/AT/CH differ in vocabulary ("Immobilienmakler" vs "Immobilientreuhänder"
  in AT). Separate pages only when the offer differs; otherwise one page, hreflang for
  currency/contact variants is not enough to avoid duplication.
- Local modifiers ("in Hildesheim", "nähe") dominate service queries for small businesses.
  One real location page per real location, not per town in a radius (doorway abuse).
- Formal register ("Sie") is the default for B2B and most B2C services; match the target
  audience notes of the project.
- Sistrix Visibility Index is the German market's standard metric for site-level trend
  comparisons; clients will quote it.

## Paid tools, one line each

- **Sistrix**: German-market standard, visibility index, keyword database, competitor overlap.
- **Ahrefs**: backlinks, keyword difficulty, SERP history, AI Overview citation tracking.
- **Semrush**: keyword magic tool, position tracking, site audit, topic research.
- **Screaming Frog**: desktop crawler, the technical audit workhorse; free up to 500 URLs.

None of them see Google's internals; all estimate volume from clickstream panels. Use them
for relative comparisons, not absolute promises.

## Output format

```
Cluster: Bodenanalyse Kosten (transactional)
Primary: bodenanalyse kosten (GSC: 340 impressions, pos 11.2)
Secondary: bodenanalyse preis, was kostet eine bodenanalyse, bodenprobe kosten landwirtschaft
SERP: 3 price guides, 1 local pack, 1 PAA block; AI Overview cites 2 pages with price tables
Owner page: /leistungen/bodenanalyse (exists, no price table, no H2 "Kosten")
Action: add price table with 3 tiers, H2 "Was kostet eine Bodenanalyse?", FAQ paragraph for PAA questions
```

## Sources

- SEO Starter Guide, "Understand what your readers want": https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- Search Console Performance report: https://support.google.com/webmasters/answer/7576553
- Google Trends: https://trends.google.com
- Bing Webmaster Tools keyword research: https://www.bing.com/webmasters/help/keyword-research-628070b6
- Creating helpful content, "Who, How, Why": https://developers.google.com/search/docs/fundamentals/creating-helpful-content
