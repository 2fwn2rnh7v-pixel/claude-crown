# `<head>`: the complete block, and what each line is for

Assembled from the measured Tesla and Apple heads (2026-09-21) plus the current platform docs.
Copy the block, replace the values, delete nothing you do not understand; read the notes instead.

```html
<!doctype html>
<html lang="de-DE">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Nordwind Modell E: E-Bike mit 180 km Reichweite | Nordwind</title>
  <meta name="description" content="Das Modell E fährt 180 km mit einer Ladung, wiegt 19 kg und ist in vier Farben ab 3.490 € erhältlich.">
  <link rel="canonical" href="https://nordwind.example/modell-e">

  <!-- language variants: one line per locale + x-default; only if the variants exist -->
  <link rel="alternate" hreflang="de-DE" href="https://nordwind.example/modell-e">
  <link rel="alternate" hreflang="x-default" href="https://nordwind.example/modell-e">

  <!-- social preview (Open Graph + X/Twitter). Image 1200x630, under 1 MB, alt text mandatory -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Nordwind">
  <meta property="og:locale" content="de_DE">
  <meta property="og:url" content="https://nordwind.example/modell-e">
  <meta property="og:title" content="Nordwind Modell E: 180 km Reichweite">
  <meta property="og:description" content="Das Modell E fährt 180 km mit einer Ladung, wiegt 19 kg und kostet ab 3.490 €.">
  <meta property="og:image" content="https://nordwind.example/og/modell-e.jpg">
  <meta property="og:image:secure_url" content="https://nordwind.example/og/modell-e.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Nordwind Modell E in Nachtblau vor der Nordseeküste">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@nordwind">
  <meta name="twitter:title" content="Nordwind Modell E: 180 km Reichweite">
  <meta name="twitter:description" content="180 km mit einer Ladung, 19 kg, ab 3.490 €.">
  <meta name="twitter:image" content="https://nordwind.example/og/modell-e.jpg">
  <meta name="twitter:image:alt" content="Nordwind Modell E in Nachtblau vor der Nordseeküste">

  <!-- icons + tiles. One SVG for modern browsers, one ICO for the rest, one 180 PNG for iOS, manifest for Android/PWA -->
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png">           <!-- 180x180, opaque, no transparency -->
  <link rel="manifest" href="/manifest.webmanifest">                    <!-- carries 192 + 512 PNG, maskable -->
  <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#171a20" media="(prefers-color-scheme: dark)">
  <meta name="msapplication-TileColor" content="#3e6ae1">              <!-- Windows Start tile background -->
  <meta name="msapplication-TileImage" content="/mstile-144x144.png">  <!-- 144x144, transparent PNG -->
  <meta name="apple-mobile-web-app-capable" content="yes">             <!-- only if the site works standalone -->
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <meta name="color-scheme" content="light dark">
  <meta name="format-detection" content="telephone=no">

  <!-- performance: the hero's chosen crop is the LCP; preload exactly that, plus the two font files in use -->
  <link rel="preload" as="image" imagesrcset="/img/hero-mobile.jpg 767w, /img/hero-desktop.jpg 3370w" imagesizes="100vw" fetchpriority="high">
  <link rel="preload" as="font" type="font/woff2" href="/fonts/text-500.woff2" crossorigin>
  <link rel="preload" as="font" type="font/woff2" href="/fonts/display-500.woff2" crossorigin>
  <link rel="preconnect" href="https://cdn.example">                    <!-- only for a real third-party origin -->

  <!-- structured data: one Product or Organization node, real values only -->
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"Product","name":"Nordwind Modell E","image":"https://nordwind.example/og/modell-e.jpg",
   "description":"E-Bike mit 180 km Reichweite","brand":{"@type":"Brand","name":"Nordwind"},
   "offers":{"@type":"Offer","priceCurrency":"EUR","price":"3490","availability":"https://schema.org/InStock","url":"https://nordwind.example/modell-e"}}
  </script>

  <link rel="stylesheet" href="/site.css">
  <script type="module" src="/site.js"></script>                        <!-- module = deferred, runs after parse -->
</head>
```

## `manifest.webmanifest`

```json
{
  "name": "Nordwind", "short_name": "Nordwind", "start_url": "/", "display": "browser",
  "background_color": "#ffffff", "theme_color": "#171a20",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

Icon set to generate from one 1024 master: `favicon.ico` (32, 16 inside), `icon.svg`,
`apple-touch-icon.png` 180, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` (safe zone =
inner 80%), `mstile-144x144.png`. Tesla ships eleven apple-touch sizes (57..152) and five PNG
favicons; that is legacy coverage for iOS 6 era devices, not something to copy. The 180 + manifest
+ SVG set covers every current platform.

## Notes, line by line

| Line | Why it is there | Common slop |
|---|---|---|
| `viewport-fit=cover` | enables `env(safe-area-inset-*)` for the persistent CTA bar and notch phones | missing, then the bar hides behind the home indicator |
| `<title>` 50-60 chars, brand last | the tab, the search result, the share card | brand first, 90 chars, em-dash separator |
| `description` 120-160 chars with one number | the search snippet | slogan without a fact |
| `canonical` absolute | dedupes `?utm` and `/index.html` variants | relative or missing |
| `hreflang` incl. `x-default` | one line per real locale; each must point back | listing locales that do not exist |
| `og:image` 1200x630 + `:width` `:height` `:alt` | the card on WhatsApp, LinkedIn, Slack, X; `:alt` is read by screen readers on X | 4000px hero reused, no alt, transparent PNG |
| `twitter:card=summary_large_image` | the large card layout; without it X falls back to small | `summary` |
| `theme-color` with `media` | browser chrome tint per scheme (Android, Safari 15+) | one colour, or the accent as tint |
| `msapplication-Tile*` | Windows pinned-site tile; cheap, harmless | the 2013 `browserconfig.xml` |
| `apple-touch-icon` 180 | iOS home screen; must be opaque | transparent PNG, then iOS paints it black |
| `manifest` | Android install, Chrome "Add to Home screen", maskable icon | missing, or `display: standalone` on a site that is not an app |
| `color-scheme` | tells the UA to render form controls / scrollbars per scheme | missing, then dark mode gets light scrollbars |
| `format-detection=telephone=no` | stops iOS from turning "180 km" style numbers into links | leaving it out on pages with many numbers |
| `preload as=image` with `imagesrcset` | the LCP starts at parse time, before CSS resolves | preloading every image, or the wrong crop |
| `preload as=font` + `crossorigin` | no FOIT/FOUT on the two faces actually used | preloading all six weights, forgetting `crossorigin` (double download) |
| JSON-LD | rich results; a Product with real price and availability | `Organization` with fake `aggregateRating` |
| `<script type=module>` | deferred by default, strict mode, no `defer` attribute needed | blocking script in `<head>` |

Delete from every template: `keywords` (ignored since 2009), `author` (no consumer), `robots`
`index,follow` (default), `X-UA-Compatible` (no IE), `MobileOptimized` / `HandheldFriendly`
(BlackBerry era; Tesla still ships them, that is inertia), `generator`.

## Verification (do this, do not trust the template)

1. `view-source:` the deployed page: every `og:` and `twitter:` value is absolute and reachable
   (`curl -I` the image, expect 200 and `image/jpeg` or `image/png`).
2. Paste the URL into the LinkedIn Post Inspector or opengraph.xyz: card shows title, image, alt.
3. `curl -s <url> | grep -c 'rel="alternate"'` equals the number of real locales.
4. Lighthouse: LCP element is the hero `<img>`, and the network panel shows it as the first image
   request (the preload worked).
5. Add the site to an iPhone home screen and a Windows Start menu once: icon is not black, not
   cropped.
