---
name: slop-eater
description: >
  Builds and audits marketing pages to the measured standard of Tesla.com and Apple.com: nav, hero
  sizing, button hover/active/focus, reveal and sticky-scrub scroll effects, art-directed images,
  persistent CTA bars, and the complete head block (meta, Open Graph, icons, tiles, manifest,
  preload). Vanilla recipes with React, Next.js, TanStack Start and Tailwind adapters, plus a scan
  script. Use ALWAYS when: a landing page, hero, product page, marketing section, nav, button set
  or scroll animation is built or changed; the user says "wie Tesla", "wie Apple", "Apple-Style",
  "premium", "Scroll-Animation", "Hover", "Meta-Tags", "OG-Image", "Favicon", "Tile", "sieht nach
  KI aus", "Slop", "landing page", "hero", "mobile design" or "Slop-Eater"; a page uses 100vh
  heroes, scroll listeners, lift-and-shadow hovers, three equal cards or em-dashes. Also trigger
  implicitly for any consumer-facing page written without anyone naming Tesla or Apple.
---

# Slop-Eater

Build and audit marketing pages the way Tesla.com and Apple.com are actually built, from
measurements taken in the browser on 2026-09-21 (`references/tesla-measured.md`,
`references/apple-measured.md`), not from the mental image of those sites. The mental image is
where the slop comes from: `100vh` heroes, parallax on scroll listeners, buttons that lift and
glow, three equal cards, an em-dash in every headline. Neither site does any of that.

Always deliver code (before/after), never only a verdict. Copy stays German where the product is
German; identifiers and comments are English.

## Three guiding rules

1. **The image sizes the hero, not the viewport.** Tesla's hero is 660px on desktop and the
   photo's own aspect on phone. Apple's tiles are 692px. Nothing jumps when the URL bar moves.
2. **Hover is one variable, not a movement.** `#3e6ae1 → #3457b1`, `#fff → #eee`, `#0071e3 →
   #0076df`. No transform, no shadow growth, no glow. Guarded by `(hover: hover)`.
3. **Nothing runs on a clock.** Every visible motion is a function of scroll position or of one
   user action, plays once, and has a static end state a full-page screenshot can show.

## Two modes

**Mode A: full audit.** The user asks ("prüf mal die Landingpage", "sieht das nach KI aus?",
"warum wirkt das billig?", "review the hero"). Run `scripts/slop_scan.py` first, then all six
levels, then the summary block. Every finding carries the measured Tesla/Apple value it is
compared against.

**Mode B: accompanying.** A page or section is being built or changed without an audit request.
Declare the design read in one line (page kind, audience, Tesla-flat or Apple-pill), build from
`references/patterns.md`, and append the compact block. Do not interrupt the user's flow.

## The six levels

### Level 1: shell, tokens, `<head>`

Three breakpoints for the whole project (600 / 900 / 1200, or Apple's 734 / 1068 / 1441), one
accent, cool greys stepped 10..70, two type faces at two weights, one duration (0.33s), one
easing (`cubic-bezier(.5,0,0,.75)`), 4px spacing base. The `<head>` is the full block from
`references/head-meta.md`: viewport with `viewport-fit=cover`, canonical, hreflang, Open Graph with
`og:image:alt`, Twitter card, SVG + ICO + 180 touch icon, manifest, `theme-color` per scheme,
`msapplication-Tile*`, LCP preload with `imagesrcset`, two font preloads, JSON-LD with real values.
Delete `keywords`, `author`, `robots index,follow`, `X-UA-Compatible`.

### Level 2: nav and hero

Nav 44-56px; white and sticky on desktop, transparent over the hero and scrolling away on phone
(Tesla) or a fixed glass bar `rgba(255,255,255,.8)` + `saturate(1.8) blur(20px)` (Apple). Hero:
art-directed `<picture>` (phone portrait, tablet portrait, landscape) with `aspect-ratio` from the
phone crop and a fixed height from 600px up; copy stack of headline, one subline, two CTAs;
copy at the top over the sky or bottom-left over a scrim, never both.

### Level 3: buttons and states

40px tall, 4px radius (Tesla) or `980px` pill with `11px 21px` padding (Apple); label 14px/500 or
17px/400 with `-0.022em`; `min-width` so labels never wrap; `:hover` swaps `--bg`, `:active` one
step darker, `:focus-visible` a 2px outline offset 2-3px, disabled `opacity: .42`. Contrast AA on
every variant including the white-on-photo one. Glass icon buttons: `rgba(255,255,255,.75)` +
`blur(4px)` + `0 4px 4px rgba(0,0,0,.25)`.

### Level 4: motion

Reveal on enter: 30px travel, 500ms, `cubic-bezier(.165,.84,.44,1)`, once, one group per section,
CSS `animation-timeline: view()` behind `@supports` with an IntersectionObserver fallback. Sticky
scrub: parent `calc(N * 100dvh)`, child `position: sticky; top: 0; height: 100dvh`, one progress
number drives transforms; the scroll listener exists only while the section is on screen and only
schedules one rAF. Video: start-frame `<picture>` under `<video muted playsinline preload="none">`
played on view, end-frame after `ended`, end-frame only under reduced motion. No parallax, no
infinite loops, no `window.addEventListener('scroll')` at page level.

### Level 5: images

One file per device (3-5 `<source media>` crops), 1x/2x or `f_auto,q_auto`, about 2x the rendered
box, `width`/`height` or `aspect-ratio` reserved, hero `fetchpriority="high"`, everything below
`loading="lazy" decoding="async"`, `object-fit: cover` for photos and `contain` for cut-outs,
`alt` with a sentence on product shots. Preload what opens instantly (menu thumbnails).

### Level 6: composition and copy

Section families, each at most once: full-bleed hero, horizontal scroll-snap rail with peek (1024
x 580 cards, dots 12px at `opacity: .5`), grey 2-up tile grid with a bleeding product shot, sticky
scrub, footer. Persistent CTA bar fixed at the bottom with `env(safe-area-inset-bottom)`, shown
after the hero leaves. Copy: no em-dash or en-dash anywhere, no fake-precise numbers, no three
equal cards, no eyebrow above every headline, CTA labels of at most three words, one label per
intent. Aesthetic direction, palette and copy voice beyond this come from `taste-skill`.

## Quick start on an existing page

```bash
python scripts/slop_scan.py <file-or-dir> [--json] [--fail-on HIGH]
```

Stdlib only. Reports, with file and line: viewport-height heroes, page-level scroll listeners,
hover rules that move or shadow, infinite animations, em/en-dashes in visible text, images without
`srcset`/`<picture>` or without reserved size, missing head lines (viewport-fit, og:image:alt,
manifest, theme-color, canonical, apple-touch-icon), dead meta (`keywords`), breakpoint sprawl (more
than three widths), three-equal-card grids, `-webkit-backdrop-filter` written by hand. A hit is a
lead; confirm at the element before it becomes a finding. Then open the page at 390 and 1440,
hover one button, scroll once, and take a full-page screenshot: what the scanner cannot see.

## Finding format (Mode A)

```
### [SEVERITY] Short description

File: path/to/file, lines X-Y
Level: [1-6] name
Problem: what is wrong and which measured Tesla/Apple value it violates.
Effect: what the visitor sees (jump, wrap, black flash, generic feel).
Correction: code before/after.
```

Severity:
- **CRITICAL**: layout jumps (100vh hero, unreserved images), motion that never settles, a hero
  the screenshot cannot show, `<head>` without viewport/canonical/og:image
- **HIGH**: hover with transform/shadow, page-level scroll listener, no reduced-motion path,
  single scaled image for all devices, missing icons/manifest/theme-color, CTA label wraps
- **MEDIUM**: breakpoint sprawl, section family repeated, em-dashes, eyebrow on every section,
  missing focus-visible, no preload for LCP
- **LOW**: dead meta lines, legacy icon sizes, font weights loaded but unused

## Summary (Mode A)

```
## Slop audit summary

Scope: [page / sections]
Overall rating: CRITICAL / HIGH / MEDIUM / LOW / CLEAN
Findings: X CRITICAL, X HIGH, X MEDIUM, X LOW

Top 3 priorities:
1. [finding + action]
2. [finding + action]
3. [finding + action]

Positive: [what already matches the measured standard]
```

## Compact format (Mode B)

```
--- Slop notes ---
Design read: <page kind> for <audience>, Tesla-flat | Apple-pill, breakpoints 600/900/1200
1. [HIGH] description -> correction
2. [MEDIUM] description -> correction
```

## Pre-flight before "done"

- Hero sized by image aspect or fixed px, never `100vh`/`100svh`; full-page screenshot shows it.
- Every button: one-line label at 390 and 1440, hover = colour only, focus ring visible, AA contrast.
- Scanner returns 0 CRITICAL and 0 HIGH on the delivered files.
- Reduced motion tested once with `matchMedia` forced; page complete without JS.
- `<head>` verified per `head-meta.md` section "Verification", not assumed.

## Agent integration

- **Agent 1 (Research)**: measure the reference the user names (playwright-cli, real Chrome
  channel; headless is blocked by Tesla): nav height, hero height at 390 and 1440, button
  computed styles at rest and `:hover`, breakpoints from the CSSOM, `<head>` inventory. Write
  the numbers down before designing anything.
- **Agent 2 (Code)**: Mode B; build from `references/patterns.md` with the tokens filled in from
  the measurement, one section family per section.
- **Agent 3 (Test/QA)**: run `scripts/slop_scan.py`, then the pre-flight in a browser at both
  widths; hover one button and read `getComputedStyle` back; screenshot before and after scroll.

## Reference files

- `references/tesla-measured.md`: every measured Tesla value (type, colours, tokens, breakpoints,
  motion, buttons with hover, layout heights, carousel, images, full `<head>`). Read for every
  Level 2, 3, 5, 6 finding.
- `references/apple-measured.md`: glass nav, pill buttons with the variable system, tile heights,
  start-frame/end-frame video, how the sticky scrub pages are built. Read for Level 3 and 4.
- `references/patterns.md`: the recipes (tokens, nav, hero, buttons, reveal, rail, grid, sticky
  scrub, CTA bar, images, reduced motion) and the React / Tailwind / template adapters. Read when
  writing any code.
- `references/head-meta.md`: the complete `<head>` block, manifest, icon set, per-line rationale,
  verification steps. Read for every Level 1 finding.

Related skills: `taste-skill` (aesthetic direction, palette, copy tells, pre-flight for the whole
page), `scroll-world` (scroll-scrubbed video chains), `seo-optimizer` (everything in SEO beyond
the head block).

## Self-reflection (MANDATORY)

At the end of every piece of work, check: is the hero height a measured number or an image
aspect, not a viewport unit? Does every hover change only colour? Is there any scroll listener
that lives longer than the section it serves? Does every animated element end in a state a
screenshot shows, with reduced motion covered? Is every image art-directed and size-reserved? Is
the `<head>` complete per `head-meta.md` and verified? Were the findings compared against the
measured values, with file and line, and the top 3 named? Is every correction runnable code?
