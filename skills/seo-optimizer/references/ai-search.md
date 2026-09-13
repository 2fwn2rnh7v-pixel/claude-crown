# Visibility in Generative AI Search

## Contents
- How AI features in Google work
- What actually helps
- Myths and what to leave out
- Outside Google: ChatGPT, Perplexity, Copilot, Claude
- AI crawlers and robots.txt
- llms.txt, soberly
- Measurement
- Agentic access
- Sources

---

## How AI features in Google work

AI Overviews and AI Mode sit on top of the existing search and ranking systems. Two
mechanisms decide what gets cited:

- **Grounding (retrieval-augmented generation)**: the model pulls pages from the existing
  Google index via the normal ranking systems and builds the answer with clickable source links.
- **Query fan-out**: the model issues additional, related queries and fetches results for
  those too. "Fix a weed-infested lawn" becomes internally "best herbicides", "remove weeds
  without chemicals", "prevent weeds".

Consequence: **there is no separate AI ranking channel.** A page that is not indexed and
not snippet-eligible cannot appear in AI features. "AEO" and "GEO" are SEO from Google's
point of view. Eligibility (doc updated 2025-12-10): indexed, eligible for a normal snippet,
no `nosnippet`/`noindex`, "no additional technical requirements".

Fan-out changes which pages get cited: studies in 2025–2026 show the overlap between AI
Overview citations and the top 10 for the *literal* query dropped from roughly 76% (Ahrefs,
July 2025) to 17–38% (BrightEdge, Ahrefs, February 2026). Citations increasingly come from
pages ranking for the fan-out sub-queries. Practical reading: cover the sub-questions of a
topic on the page (or in the cluster), not just the head term. Do **not** build one page per
imaginable sub-query; that is scaled content abuse.

## What actually helps

Google's own list (AI-features optimisation guide, updated 2026-07-10):

1. **Own point of view.** When several sources could be cited, the one that contributes
   something is preferred over the one that summarises others. Experience report over digest.
2. **Clean technical base.** Crawlable, indexable, server-rendered, not duplicated.
3. **Clear structure for people.** Paragraphs, subheadings, direct answers to concrete
   questions, because that is what good pages look like, not because "chunking" is needed.
4. **Images and videos** that support the text; AI features surface them.
5. **Semantic HTML**, primarily for screen readers and agents; perfect validity is not needed.
6. **Good page experience** across devices.
7. **Merchant Center / Business Profile** where products or local services are involved.

## Myths and what to leave out

Google names these explicitly as **not** necessary:

- `llms.txt` or other "AI files" and special markup. Google Search does not read them.
- Splitting content into small "chunks". There is no ideal page length.
- Rewriting text specifically for AI systems. Synonyms are understood.
- Buying or seeding artificial "mentions" across the web.
- Over-focusing on structured data. Helpful for rich results, not a requirement for AI features.
- Creating multiple content variations to target fan-out queries. Falls under scaled content abuse.

Also: no third-party tool has access to Google's internal ranking or AI systems. Promises
about "internal metrics" or "AI visibility scores" are unverifiable. Report them as such.

## Outside Google: ChatGPT, Perplexity, Copilot, Claude

- **ChatGPT search** retrieves through Bing's index plus OpenAI's own `OAI-SearchBot`
  crawling. A page missing from Bing is invisible there and in Microsoft Copilot. Verify the
  site in Bing Webmaster Tools, submit the sitemap, enable IndexNow.
- **Perplexity** runs its own index via `PerplexityBot`; allow it in robots.txt and WAF if
  citations matter.
- **Claude** fetches pages on demand via `Claude-User` and indexes via `Claude-SearchBot`.
- All of them weight the same things as Google's guide: clear answers near the top, original
  data, named authors, recent dates, consistent entity information. Reddit and YouTube are
  heavily cited; a presence there is a legitimate, non-spammy lever for brands.

## AI crawlers and robots.txt

Three access types to consider separately:

| Bot type | Examples | Purpose | Honours robots.txt |
|---|---|---|---|
| Training crawlers | `GPTBot`, `ClaudeBot`, `CCBot`, `Google-Extended`, `Applebot-Extended`, `meta-externalagent`, `Bytespider` | Model training | Yes (Bytespider: unreliable) |
| Search/index crawlers | `OAI-SearchBot`, `PerplexityBot`, `Claude-SearchBot`, `Googlebot` | Index for the provider's answer search | Yes |
| User-triggered fetchers | `ChatGPT-User`, `Claude-User`, `Perplexity-User` | On-demand fetch of one URL for a user | Generally no (user request) |

`Google-Extended` controls only use for Gemini training and grounding and "does not impact a
site's inclusion in Google Search nor is it used as a ranking signal" (Google, 2026-07-14).
Blocking it does not remove the site from AI Overviews.

Pattern when training is excluded but citability kept:

```
User-agent: GPTBot
User-agent: ClaudeBot
User-agent: CCBot
User-agent: Google-Extended
User-agent: Applebot-Extended
User-agent: meta-externalagent
Disallow: /

User-agent: OAI-SearchBot
User-agent: PerplexityBot
User-agent: Claude-SearchBot
Allow: /
```

robots.txt is a voluntary agreement (RFC 9309), not access control. Enforcement happens at
server or CDN level, and both layers must agree. **Cloudflare blocks AI crawlers by default
for new zones (since 2025-07-01) and, from 2026-09-15, blocks mixed-use crawlers on pages
with ads for new zones and free plans.** A CDN that blocks while robots.txt allows is the most
common and hardest-to-find mismatch. Check the dashboard, then server logs by user agent.

Google's own crawlers relevant here: `Googlebot` (Search incl. AI features), `GoogleOther`
(R&D, not Search), `Google-CloudVertexBot` (Vertex AI agents), `Google-Extended` (see above).

## llms.txt, soberly

Facts as of September 2026:

- Google does not use the file and does not plan to (Illyes, Mueller, July 2025; Mueller
  compared it to the keywords meta tag).
- No major provider (OpenAI, Anthropic, Google, Meta, Perplexity) documents it as a citation
  or ranking signal.
- Log studies: Ahrefs (137k sites) found about 97% of `llms.txt` files with zero bot
  requests; a 90-day study of 500M AI bot hits found 408 requests for the file.
- Adoption about 10% of domains (SE Ranking, 300k domains, 2026).

What still speaks for it: coding agents and IDE tools (Cursor, Continue, Cline) and MCP
integrations do read it; for developer documentation it saves tokens. Effort minimal, damage
zero.

**Recommendation**: ship it when the framework generates it or the site is developer docs.
Never sell it as an SEO or visibility measure, never prioritise it while technical blockers
are open. In reports it belongs under "Not relevant (deliberately dropped)".

## Measurement

- Search Console → **Generative AI performance report** (launched 2026-06-03, worldwide since
  2026-08-31): impressions in AI Overviews, AI Mode and AI features in Discover, by page,
  country, device, date. **No clicks, no queries.** AI-feature clicks remain inside the normal
  Performance → Web numbers.
- Search Console → Settings → **Search generative AI control**: property-level opt-out from
  AI Overviews/AI Mode/Discover AI. Google: not a ranking signal elsewhere, no effect on training.
  Default is "included". Do not toggle it without the owner's explicit decision.
- Server logs grouped by user agent: real AI crawler activity, and whether the CDN lets them in.
- Analytics: referrer traffic from `chatgpt.com`, `perplexity.ai`, `claude.ai`,
  `copilot.microsoft.com`, `gemini.google.com`. Gemini and AI Mode traffic mostly arrives as
  `google.com` organic; do not promise a clean split.
- Not measurable, do not promise: a "position" in AI Overviews, a share of voice inside ChatGPT.

## Agentic access

Browser agents use screenshots, DOM and the accessibility tree. What helps them overlaps
almost entirely with classic accessibility: real `<button>`/`<a>` elements, labels on form
fields, stable ARIA roles, no icon-only controls without names, no state changes only on
hover, no content that appears only after a consent click.

Further reading: https://web.dev/articles/ai-agent-site-ux

## Sources

- Optimizing for generative AI on Google Search (updated 2026-07-10): https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- AI features and your website (updated 2025-12-10): https://developers.google.com/search/docs/appearance/ai-features
- Generative AI performance reports (2026-06-03): https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports
- Generative AI performance report help: https://support.google.com/webmasters/answer/16984139
- Evaluating third-party SEO advice: https://developers.google.com/search/docs/fundamentals/third-party-seo
- Google common crawlers incl. Google-Extended (updated 2026-07-14): https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers
- OpenAI crawlers: https://developers.openai.com/api/docs/bots
- Anthropic crawlers: https://support.claude.com/en/articles/8896518
- Perplexity crawlers: https://docs.perplexity.ai/guides/bots
- Ahrefs llms.txt study: https://ahrefs.com/blog/llmstxt-study/
- AI Overview citation overlap studies: https://www.brightedge.com/resources/weekly-ai-search-insights/rank-overlap-after-16-months-of-aio, https://www.searchenginejournal.com/google-ai-overview-citations-from-top-ranking-pages-drop-sharply/568637/
- llms.txt specification: https://llmstxt.org
- Agent-friendly sites: https://web.dev/articles/ai-agent-site-ux
