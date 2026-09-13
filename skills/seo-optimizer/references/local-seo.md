# Local SEO (small businesses, German-speaking markets)

## Contents
- When local applies
- Google Business Profile: the non-negotiables
- NAP consistency and the Impressum
- Reviews: policy and practice
- Location pages on the site
- LocalBusiness structured data
- Beyond Google
- Measurement
- Sources

---

## When local applies

Local ranking systems trigger when the query or the searcher's location implies a place:
"friseur hildesheim", "restaurant in der nähe", "immobilienmakler" from a phone in Hannover.
Three factors, per Google: **relevance** (does the profile match the query), **distance**
(from the searcher or the named place), **prominence** (how well-known: reviews, links,
mentions, directory presence). A studio, restaurant, salon, agency with a visitable address
or a defined service area is a local business; a purely remote SaaS is not.

## Google Business Profile: the non-negotiables

1. Claim and verify the profile (video verification is now common; have the storefront,
   signage and tools ready).
2. Primary category = what the business *is* (`Webdesigner`, `Restaurant`, `Kosmetikstudio`),
   secondary categories for what it also does. The primary category is the strongest
   relevance lever.
3. Exact name as on the signage and Impressum. No keyword stuffing in the name ("Friseur
   Hildesheim Beste Preise"). That violates the guidelines and gets suspended.
4. Address (or service area for businesses without walk-in), phone, website URL with UTM
   parameters for attribution (`?utm_source=google&utm_medium=organic&utm_campaign=gbp`).
5. Opening hours, including holiday hours. Wrong hours are the fastest way to a 1-star review.
6. Real photos, updated quarterly; logo and cover. Stock images get removed.
7. Products/services with prices, description in the audience's language, attributes.
8. Answer Q&A yourself and seed the first questions.
9. Posts are optional; reviews and photos matter more.

## NAP consistency and the Impressum

Name, address, phone must be character-identical across: Google Business Profile, website
footer, Impressum, `LocalBusiness` JSON-LD, Apple Business Connect, Bing Places, the main
directories (Gelbe Seiten, 11880, Das Örtliche, Yelp, branch portals). "Straße" vs "Str.",
"+49 5121" vs "05121" are inconsistencies for matching systems. Pick one form, use it everywhere.

The German Impressum obligation (§ 5 DDG, formerly TMG) and the privacy policy are legal
requirements that double as trust signals: operator, address, contact, register entry, VAT ID.
A missing or hidden Impressum is a trust defect in E-E-A-T terms and a legal risk. Link it
from every page footer, reachable in one click.

## Reviews: policy and practice

Google's contribution policy: asking customers for reviews is allowed; **offering incentives
(discounts, gifts, contests) for reviews is not**; selectively asking only happy customers
("review gating") is not; reviews from employees, the owner or on the owner's device are not.
Fake or bought reviews lead to review removal and profile restrictions.

Practice: a short link (`g.page/r/…/review`) or QR code at the point of delivery, a follow-up
email 2–3 days after the service, a reply to every review within days (also the bad ones, in
a calm register). Review velocity and recency count more than the total.

Marking up third-party reviews (Google, Yelp) as `aggregateRating` on the own site is a
policy violation; only first-party reviews collected and displayed on the site qualify.

## Location pages on the site

- One page per real location with a unique address, hours, photos of *that* location, staff,
  directions, parking, embedded map, local phone number. Not a template with the city name swapped.
- Service-area businesses: one page per service, the areas listed inside it. No page per
  town in a radius (doorway abuse).
- The homepage of a single-location business *is* the location page; put NAP in the footer
  and the `LocalBusiness` node on it.
- Title pattern: `Service in Stadt – Nutzen | Marke`. H1 names service and place once.
- Link the Google Business Profile (`sameAs`) and link back from the profile to the page.

## LocalBusiness structured data

Use the most specific subtype (`Restaurant`, `HairSalon`, `BeautySalon`, `RealEstateAgent`,
`Store`, `ProfessionalService` for agencies). Full template in `assets/jsonld/localbusiness.json`.
Required for the rich result: `name`, `address`, and either `url` or `telephone`. Recommended:
`geo`, `openingHoursSpecification`, `image`, `priceRange`, `sameAs`, `hasMap`. Values must
match what is visible on the page and in the profile.

## Beyond Google

- **Apple Business Connect**: Apple Maps and Siri; free, claim it.
- **Bing Places**: import from Google Business Profile; feeds Bing, Copilot and ChatGPT search
  local answers.
- **Industry portals** with real traffic (Tripadvisor, Immobilienscout24, Treatwell, Lieferando
  depending on the vertical) are both citations and lead sources.
- AI assistants answer "best X near Y" from profiles, reviews and directory data. The same
  hygiene applies.

## Measurement

- Google Business Profile → Performance: searches (branded vs discovery), calls, direction
  requests, website clicks. Export monthly; the UI only shows 6 months.
- Search Console: queries containing the city name, filtered by the location page.
- UTM-tagged profile link in GA4 to separate profile traffic from organic.
- Rank checking by location needs a tool with geo-grid (Local Falcon, BrightLocal); otherwise
  spot-check with a VPN or the `&near=` parameter, understanding it is approximate.

## Sources

- Local ranking factors (Google): https://support.google.com/business/answer/7091
- Business Profile guidelines: https://support.google.com/business/answer/3038177
- Prohibited and restricted content, reviews: https://support.google.com/contributionpolicy/answer/7400114
- Local business structured data: https://developers.google.com/search/docs/appearance/structured-data/local-business
- Review snippet policies: https://developers.google.com/search/docs/appearance/structured-data/review-snippet
- Apple Business Connect: https://businessconnect.apple.com
- Bing Places: https://www.bingplaces.com
- Impressum duty § 5 DDG: https://www.gesetze-im-internet.de/ddg/__5.html
