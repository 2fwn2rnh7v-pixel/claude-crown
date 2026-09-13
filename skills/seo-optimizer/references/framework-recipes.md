# Framework Recipes (TypeScript web apps)

## Contents
- Rendering decision
- Next.js App Router (16.x)
- TanStack Start / TanStack Router
- Astro
- React Router v7 (framework mode)
- React SPA / Vite
- Hosting: 404, redirects, headers
- Images
- Third-party scripts and consent
- Deploy checks
- Sources

---

## Rendering decision

| Page type | Recommendation |
|---|---|
| Marketing, blog, docs | SSG (prerendered at build) |
| Catalogue / list pages with frequent changes | ISR / revalidation |
| Personalised views | SSR, usually `noindex` |
| App behind login | client-side, excluded via robots.txt and `noindex` |

Rule: everything that should rank is delivered server-rendered. Verify with `curl`, not by
reading the component.

## Next.js App Router (16.x)

**Metadata per route** (`app/preise/page.tsx`):

```ts
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Preise – Bodenanalysen ab 89 € | Agrarmonitor",
  description:
    "Transparente Preise für Bodenanalysen inklusive Probenahme, Labor und Auswertung. Ohne Grundgebühr, monatlich kündbar.",
  alternates: { canonical: "/preise" },
  openGraph: {
    title: "Preise – Bodenanalysen ab 89 €",
    description: "Transparente Preise inklusive Probenahme und Auswertung.",
    url: "/preise",
    type: "website",
    images: [{ url: "/og/preise.png", width: 1200, height: 630 }],
  },
};
```

`metadataBase` once in the root layout so relative URLs resolve absolutely. Title template
there too. `viewport`, `themeColor`, `colorScheme` moved to `generateViewport` (deprecated
inside `metadata` since 14):

```ts
export const metadata: Metadata = {
  metadataBase: new URL("https://domain.tld"),
  title: { default: "Agrarmonitor", template: "%s | Agrarmonitor" },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1 };
```

**Dynamic routes**: `generateMetadata`, and `notFound()` when data is missing. That yields a
real 404 instead of a 200 page with error text.

```ts
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const item = await getItem(slug);
  if (!item) notFound();
  return { title: item.title, description: item.excerpt, alternates: { canonical: `/leistungen/${slug}` } };
}
```

**Streaming metadata**: when `generateMetadata` is slow, Next streams the page and appends the
metadata tags to `<body>` for JS-capable bots (Googlebot). HTML-limited bots detected by UA
(`facebookexternalhit`, Twitterbot, …) get a blocking render. Custom list via
`htmlLimitedBots` in `next.config.ts`; `htmlLimitedBots: /.*/` disables streaming entirely.
Audit both views. With Cache Components, metadata that touches runtime data defers to request
time; use `'use cache'` in `generateMetadata` when it only needs external data.

**Sitemap** (`app/sitemap.ts`): only published, indexable entries; `lastModified` from real
data, never `new Date()` for every URL.

```ts
import type { MetadataRoute } from "next";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const items = await getPublishedItems();
  return [
    { url: "https://domain.tld", lastModified: siteUpdatedAt },
    ...items.map((i) => ({ url: `https://domain.tld/leistungen/${i.slug}`, lastModified: i.updatedAt })),
  ];
}
```

**robots.txt** (`app/robots.ts`):

```ts
import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/api/", "/app/", "/admin/"] }],
    sitemap: "https://domain.tld/sitemap.xml",
  };
}
```

**JSON-LD** rendered in the server component so it is in the HTML without client JS:

```tsx
<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c") }} />
```

**Exclude from index**: `export const metadata: Metadata = { robots: { index: false, follow: false } };`

## TanStack Start / TanStack Router

Head tags come from the route option `head()`; the root route renders `<HeadContent />` in
`<head>` and `<Scripts />` at the end of `<body>`. Child routes override `title` and meta
with the same `name`/`property`; other tags merge.

```tsx
// routes/__root.tsx
import { createRootRoute, HeadContent, Outlet, Scripts } from "@tanstack/react-router";

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Agrarmonitor" },
    ],
    links: [{ rel: "icon", href: "/favicon.ico" }],
  }),
  component: () => (
    <html lang="de">
      <head><HeadContent /></head>
      <body><Outlet /><Scripts /></body>
    </html>
  ),
});
```

```tsx
// routes/preise.tsx
export const Route = createFileRoute("/preise")({
  loader: () => getPrices(),
  head: ({ loaderData }) => ({
    meta: [
      { title: `Preise ab ${loaderData.from} € | Agrarmonitor` },
      { name: "description", content: "Transparente Preise für Bodenanalysen." },
      { property: "og:title", content: "Preise – Bodenanalysen" },
    ],
    links: [{ rel: "canonical", href: "https://domain.tld/preise" }],
    scripts: [{ type: "application/ld+json", children: JSON.stringify(jsonLd) }],
  }),
  component: PricesPage,
});
```

- Scripts listed in `head().scripts` render in `<head>`; `routeOptions.scripts` renders at the
  end of `<body>`. JSON-LD belongs in `head().scripts`.
- Not-found: `throw notFound()` in the loader; the root `notFoundComponent` renders, and the
  server responds 404 when the Start server handler sees the not-found state. Verify with
  `curl -I`.
- Prerender marketing routes at build (`prerender` option in the Start config) so the HTML
  exists without a runtime; the Worker still serves SSR for the rest.
- `robots.txt` and `sitemap.xml`: static files in `public/`, or server routes that read the
  same route list as the app so they never diverge.

## Astro

- `<title>`, meta and canonical in the layout `<head>` from props; `Astro.url` for the
  canonical, `Astro.site` must be set in `astro.config.mjs` for absolute URLs.
- `@astrojs/sitemap` generates `sitemap-index.xml`; filter drafts and `noindex` pages in its
  `filter` option.
- `public/robots.txt` static, or a `robots.txt.ts` endpoint.
- JSON-LD: `<script type="application/ld+json" set:html={JSON.stringify(jsonLd)} />`.
- 404: `src/pages/404.astro` is served with status 404 by supported adapters; verify on the host.
- Islands are fine; text content must be in the static HTML, not only inside a client island.

## React Router v7 (framework mode)

```tsx
export function meta({ data }: Route.MetaArgs) {
  return [
    { title: data.title },
    { name: "description", content: data.description },
    { tagName: "link", rel: "canonical", href: `https://domain.tld${data.path}` },
    { "script:ld+json": jsonLd },
  ];
}
export function loader({ params }: Route.LoaderArgs) {
  const item = getItem(params.slug);
  if (!item) throw new Response("Not Found", { status: 404 });
  return item;
}
```

`prerender: [...]` in `react-router.config.ts` for static marketing routes; `ssr: true` for
the rest.

## React SPA / Vite

Without prerendering an SPA is structurally disadvantaged. Options, descending quality:

1. Move marketing routes to a framework with SSR/SSG (TanStack Start, Next.js, Astro, React
   Router framework mode). Often only those routes need to move.
2. Build-time prerendering for the public routes (Vike, `vite-react-ssg`, `vite-plugin-prerender`).
3. A separate static marketing site in front of the app; app under `/app` with `noindex`.

`react-helmet-async` or `document.title` only take effect when the page is rendered
server-side or at build time. In pure client rendering they are a gamble, and Bing sees
nothing. Routers' `<Link>` renders real `<a href>`; avoid custom onClick navigation.

## Hosting: 404, redirects, headers

| Host | Real 404 for unknown routes | Redirects | Headers (X-Robots-Tag etc.) |
|---|---|---|---|
| Cloudflare Workers static assets | `assets.not_found_handling = "404-page"` + `404.html`; SPA mode answers **200** | in the Worker (`Response.redirect(url, 301)`) or Rules | Worker or `_headers` |
| Cloudflare Pages | `404.html` at root | `_redirects` (`/alt /neu 301`) | `_headers` |
| Vercel | framework 404 (`notFound()`); rewrites to `index.html` answer 200 | `vercel.json` `redirects` with `permanent: true` (308) | `vercel.json` `headers` |
| Netlify | `/* /404.html 404` last rule | `_redirects` with status | `_headers` |

Use 308 or 301 for permanent moves; 307/302 for temporary. Never a meta refresh.
`X-Robots-Tag: noindex` for PDFs, feeds and preview deployments. Preview/staging hosts:
`noindex` via header **and** password or IP allow-list; and make sure that header does not ship
to production (`crawl_check.py` → `URL_NOINDEX`).

## Images

- `width`/`height` or `aspect-ratio` always (CLS). Next.js `<Image>`, Astro `<Image>`, or
  plain `<img>` with attributes.
- LCP image: `fetchpriority="high"` (Next.js `priority`), **no** `loading="lazy"`. Everything
  below the fold lazy.
- Modern formats (AVIF/WebP), responsive `sizes`, 2× display size maximum.
- `alt` describes content; decorative images `alt=""`.
- Descriptive file names: `bodenanalyse-probenahme.webp`.
- Self-hosted, same origin or a preconnected CDN; no third-party image host without
  `<link rel="preconnect">`.

## Third-party scripts and consent

Analytics, consent layer and chat widgets are the most common INP and LCP cause.

- Load non-critical scripts deferred: Next.js `<Script strategy="lazyOnload">`, otherwise
  `defer` or after `load`. Facades for video and map embeds.
- Consent banner: render with reserved space (no CLS), inline critical styles, no layout
  dependency on a remote script. Content must not be hidden behind the banner for crawlers
  (Googlebot does not click "accept"; a consent wall that hides the main text is a cloaking
  and indexing problem).
- Consent Mode v2 (EU): without consent, GA4 collects modelled data only; expect gaps in
  organic landing-page reporting and say so in reports.
- Self-host fonts; third-party font requests are a GDPR and a performance issue.

## Deploy checks

Before every production deploy:

```bash
# No staging/preview canonical in the build
grep -r 'rel="canonical"' dist/ | grep -v 'https://domain.tld'

# No accidental noindex outside the app area
grep -r 'noindex' dist/ | grep -v '/app/'

# H1 present without JS
curl -sL https://domain.tld/preise | grep -i '<h1'

# Status codes: real 404, single-hop redirect, robots and sitemap reachable
python scripts/crawl_check.py https://domain.tld --limit 50
```

A `noindex` or preview canonical from the staging config that ships to production is the
most expensive and most common single error in this area. Make it a CI gate:
`seo_check.py dist/ --base-url https://domain.tld --fail-on error`.

## Sources

- Next.js Metadata (16.x): https://nextjs.org/docs/app/api-reference/functions/generate-metadata
- Next.js generateViewport: https://nextjs.org/docs/app/api-reference/functions/generate-viewport
- Next.js sitemap.ts: https://nextjs.org/docs/app/api-reference/file-conventions/metadata/sitemap
- Next.js robots.ts: https://nextjs.org/docs/app/api-reference/file-conventions/metadata/robots
- Next.js htmlLimitedBots: https://nextjs.org/docs/app/api-reference/config/next-config-js/htmlLimitedBots
- TanStack Router document head management: https://tanstack.com/router/latest/docs/framework/react/guide/document-head-management
- TanStack Start: https://tanstack.com/start/latest
- Astro sitemap: https://docs.astro.build/en/guides/integrations-guide/sitemap/
- React Router meta: https://reactrouter.com/start/framework/route-module#meta
- Cloudflare Workers static assets routing: https://developers.cloudflare.com/workers/static-assets/routing/
- JavaScript SEO (Google): https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Google Images: https://developers.google.com/search/docs/appearance/google-images
