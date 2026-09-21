# Tesla.com, measured

Measured 2026-09-21 on `https://www.tesla.com/de_de/` with playwright-cli (real Chrome channel, headed;
headless Chromium is blocked by Akamai with 403). Desktop 1440x900, mobile 390x844, DPR 1.
Every value below is a computed style or a DOM fact, not a guess. Re-measure before quoting a
number as "current"; Tesla ships new frontends often (this one: Drupal 10 + TDS design system +
`tcl-react` 1.31.6).

## What Tesla is NOT doing (kills three common assumptions)

| Assumption | Measured reality |
|---|---|
| Hero is `100vh` | Hero is **660px** on a 900px viewport (desktop), **691.6px** on mobile = the art-directed image's own aspect (767x1404 scaled to 375 wide). Height comes from the image, not the viewport. |
| Homepage uses scroll-snap | Container class is literally `tcl-homepage-no-scroll-snapping`. `scroll-snap-type: none` on html and body. Snap only lives inside the horizontal carousel. |
| Parallax / scroll-scrubbed hero | Body carries `tcl-parallax-effect--off`. No `animation-timeline`, no canvas, no scroll-scrubbed video on the homepage. Motion = reveal-on-enter + 0.33s transitions. |
| Big glassy nav | Header is **56px**, `background: transparent` at top on mobile, white on desktop/tablet (`tds-site-header--white-background--desktop`), sticky on desktop and tablet only (`tds-menu-header--sticky-without-slide--desktop`), scrolls away on phone. |

## Type

| Role | Family | Size / line | Weight | Note |
|---|---|---|---|---|
| Body | `"Universal Sans Text", -apple-system, Arial, sans-serif` | 14px / 20px | 400 | `html { font-size: 14px }`, color `#393c41` |
| Display (H1 hero, desktop) | `"Universal Sans Display", ...` | 56px / 56px | 500 | `letter-spacing: normal`, `text-shadow: none`, white on photo |
| H1 hero, mobile | same | 40px / 48px | 500 | |
| Carousel card title | same | 48px / 56px | 500 | white, on `tds-scrim--black` |
| Grey card title (desktop) | same | 34px / 44px | 500 | `#171a20` |
| Grey card title (mobile) | same | 28px / 36px | 500 | |
| Hero subline (H4) | Display | 20px / 28px | 400 | |
| Nav item | Text | 14px / 20px | 500 | `#171a20`, `padding: 4px 16px`, `border-radius: 4px` |
| Footer link | Text | 12px / 20px | 500 | `#5c5e62` |
| Button label | Text | 14px / 16.8px | 500 | |

Loaded weights: Display 400/500, Text 400/500 only. 700/300/100 declared but `unloaded`.
Type scale tokens: `--tds-font-size-30..110` = 14, 17, 20, 24, 28, 40, 48, 56, 64.

## Colour tokens (resolved)

```
--tds-theme-primary               #3e6ae1   primary button
--tds-theme-primary-highlight     #3457b1   primary button :hover
--tds-theme-foreground            #393c41   body text (grey20)
--tds-theme-foreground-high-contrast #171a20 headings, nav (grey10)
--tds-theme-background            #fff
--tds-theme-background-container  #f4f4f4   grey cards (grey70)
--tds-theme-background-container-alt #0000000d  nav item hover pill (5% black)
--tds-color--tertiary-highlight   #eee      white button :hover
--tds-color--grey30               #5c5e62   footer text
--tds-color--grey40               #a2a3a5
--tds-color--grey50               #d0d1d2   floating CTA border
--tds-color--grey60               #e2e3e3
--tds-outline--focus              2px solid #8e8e8e
```

Greys are cool and stepped: 10/20/30/40/50/60/70. One accent. Nothing else coloured in the UI;
red lives only in the photographs.

## Spacing tokens

`--tds-size--half` 4, `1x` 8, `2x` 16, `3x` 24, `4x` 32, `6x` 48, `8x` 64.
Content gutter `--tds-content_container--gutter`: **48px desktop, 24px mobile**.
Card copy padding: 40px (carousel card), hero copy `padding: 64px 24px 24px` (mobile).

## Breakpoints

Three widths, used consistently: **600 / 900 / 1200**.

```
(max-width: 599px)                          phone
(min-width: 600px) and (max-width: 899px)   tablet
(min-width: 900px)                          desktop
(min-width: 1200px)                         wide
(hover: hover)                              gates every hover rule
(prefers-reduced-motion: no-preference)     gates the animations
(prefers-reduced-motion: reduce)            static overrides
```

Art-directed pictures add orientation: `(max-width: 599px) and (orientation: portrait)`,
`(max-height: 599px) and (orientation: landscape)`, `(min-width: 600px) and (orientation: portrait)`,
`(min-width: 900px) and (orientation: landscape)`.

## Motion

| Token | Value |
|---|---|
| Base transition | `0.33s` (colour, background, border, box-shadow 0.25s) |
| Easing | `--tds-bezier: cubic-bezier(0.5, 0, 0, 0.75)` |
| Marketing easing (reveals) | `--tds-animate-transition-function--mktg: cubic-bezier(0.165, 0.84, 0.44, 1)` |
| Reveal durations | short `500ms`, long `1500ms` |
| Header bg/shadow | `transition: background-color 0.33s, box-shadow 0.33s` |
| Sticky bar | `transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out` |
| Page fade | `--tds--fade-in: tds--fade-in 1s ease` on `header.tds--fade-in` |

Reveal-on-enter, the only scroll effect on the page:

```css
.tds-animate_small--to_reveal { opacity: 0; transform: translate3d(0, 30px, 0);
  transition: transform 500ms cubic-bezier(.165,.84,.44,1), opacity 500ms cubic-bezier(.165,.84,.44,1); }
.tds-animate_large--revealed  { opacity: 1; transform: translateZ(0);
  transition: transform 1500ms cubic-bezier(.165,.84,.44,1), opacity 1500ms ...; }
```

The class swap is driven by an observer (body carries `animate-onscroll`). 30px travel, not 100.
Keyframes present but decorative only: `tds-keyframe--bounce` (down arrow, 2s infinite, 5px),
`tds--fade-in`, `tds--pulsing`, `showCta`/`hideCta` (0.25s) for the mobile permanent CTA.

## Buttons (`.tds-btn`)

Base, measured on the hero CTAs:

```
height 40px           border-radius 4px       padding 4px (label centred by flex)
font 14px/16.8px 500  border 2.4px solid transparent   min-width auto
width: 200px (hero desktop) / 160px (carousel card) / 180px (grey card) / 159.5px (hero mobile, 2-up)
transition: border-color .33s, background-color .33s, color .33s, box-shadow .25s
box-shadow: inset 0 0 0 2px transparent   (focus ring slot, coloured on :focus)
display flex; align-items center; justify-content center
```

Variants and their measured hover (hovered with the mouse, read back via `:hover`):

| Variant | Rest | Hover | Rule |
|---|---|---|---|
| `--primary` | `#3e6ae1` / white | `#3457b1` / white | `--tds-btn--background-color: var(--tds-theme-primary-highlight)` |
| `tcl-btn--high-contrast` (white) | `#fff` / `#393c41` | `#eee` / same | `--tds-color--tertiary-highlight` |
| `--tertiary` | `#fff` / `#393c41` | `#eee` | same token |
| `--secondary` | transparent, border | fills `#171a20`, text inverse | `.tds-btn--secondary:hover { --tds-btn--background-color: foreground-high-contrast; color: inverse }` |
| Icon button `.tds-icon-btn` | `rgba(255,255,255,.75)`, `backdrop-filter: blur(4px)`, `box-shadow: 0 4px 4px rgba(0,0,0,.25)`, 40x40, radius 4 | bg `#0000000d` + `blur(16px)` | under `@media (hover: hover)` |

No transform on hover. No scale. No shadow growth. The hover is one variable swap behind
`(hover: hover)` plus `cursor: pointer`. Focus: `box-shadow: inset 0 0 0 2px` (colour from the
variant) and `outline: none`; the `replicant` theme uses `outline: 2px solid #8e8e8e; outline-offset: 2px`.

Nav item hover: `.tds-site-nav-item` gets `.tds--hovered`, background `#0000000d` (5% black), radius 4,
and the mega menu slides in (`dx-mega-menu__slide-in`) with the page content blurred behind a white panel.

## Layout of the homepage (desktop, 7 sections, 3926px total)

| # | Block | Height | What it is |
|---|---|---|---|
| 1 | Hero carousel | 660 | full-bleed `<picture>`, centred copy at top (H1 56, H4 20, note 14), 2 CTAs 200px, arrows 40x40 glass, dots |
| 2 | Product card carousel | 664 | `overflow-x: scroll; scroll-snap-type: x mandatory; scrollbar-width: none; scroll-behavior: smooth`; slides 1024x580, `scroll-snap-align: start`, next card peeks at the right edge; copy bottom-left, `padding: 40px`, `tds-scrim--black`; 12px dots, inactive `opacity: .5` |
| 3 | Grey 2-up grid | 340 | cards `#f4f4f4`, `border-radius: 8px`, `overflow: hidden`, `display: flex`, 652px wide, 292 tall, product photo bleeds out of the card (img 217x800, `object-fit: contain`) |
| 4 | FSD tile | 660 | full-bleed picture, one CTA |
| 5 | spacer | 80 | |
| 6 | Powerwall carousel | 808 | same as #2 |
| 7 | Footer | 528 | white, 12px links |

Mobile: same order, hero 691.6, cards stack image-top/text-bottom (351x380, radius 8), carousel
slides 330 wide with peek, buttons 2-up (159.5 + 8 gap + 159.5 = 327 = 390 - 2x24 - scrollbar).
Even Tesla wraps "Weitere Informationen" to two lines in a 159px button. Do not copy that.

## Persistent CTA (both viewports)

```
.tcl-sticky-bar { position: fixed; left: 0; right: 0; bottom: 60px (desktop) / 68px (mobile);
  z-index: 10; display: flex; justify-content: center; padding: 10px 24px (desktop) / 14px 24px (mobile);
  transform: translateY(100%); transition: transform .3s ease-in-out, box-shadow .3s ease-in-out; }
.tcl-sticky-bar--scroll { transform: translateY(60px) }   /* class toggled by scroll position */
.tcl-sticky-bar__button { height 40; background #f4f4f4; border .8px solid #d0d1d2; radius 4;
  padding 4px 24px; font 14/500; display flex; gap 10px; width 236px desktop / 321px (full) mobile }
```

Mobile menu trigger: `Menü` pill 69x32, `background: rgba(0,0,0,.05)`, `backdrop-filter: blur(16px)`,
radius 4, white text over the dark hero. Opens a full-screen white sheet (back arrow, title, close).

## Images

Every marketing image is a `<picture>` with **four art-directed sources**, one file per device,
not one file scaled:

```html
<picture>
  <source media="(max-width: 599px) and (orientation: portrait)"   srcset=".../f_auto,q_auto/Homepage-Promo-Model-Y-Mobile-EMEA-LHD.jpg">
  <source media="(max-height: 599px) and (orientation: landscape)" srcset=".../Homepage-Promo-Model-Y-Desktop-EMEA-LHD.jpg">
  <source media="(min-width: 600px) and (orientation: portrait)"   srcset=".../Homepage-Promo-Model-Y-Tablet-EMEA-LHD.jpg">
  <source media="(min-width: 900px) and (orientation: landscape)"  srcset=".../Homepage-Promo-Model-Y-Desktop-EMEA-LHD.jpg">
  <img src=".../Homepage-Promo-Model-Y-Desktop-EMEA-LHD.jpg" alt="Model Y">
</picture>
```

- CDN transforms in the URL: `f_auto,q_auto` (format + quality negotiated per browser), menu
  thumbnails `w_220,c_scale/dpr_2.0`.
- Natural sizes: hero desktop 3370x1430, card 2304x1305 (shown at 1024x580 = 2.25x), mobile hero
  767x1404. Roughly 2x the rendered size, never 4x.
- `object-fit: cover; object-position: 50% 50%` on hero/card images; `contain` on cut-out product shots.
- Hero images load eagerly (`loading="auto"`); no `fetchpriority` attribute measured.
- Mega-menu thumbnails are `<link rel="preload" as="image">` in the head (16 of them), so the menu
  opens without a flash.
- No `<video>` on the homepage at measurement time.

## `<head>` (the complete measured set)

Meta: `charset=utf-8`, `viewport=width=device-width, minimum-scale=1.0, initial-scale=1.0, shrink-to-fit=no, viewport-fit=cover`,
`description`, `theme-color=#000000`, `apple-mobile-web-app-capable=yes`, `apple-mobile-web-app-status-bar-style=black`,
`msapplication-TileColor=#cc0000`, `msapplication-TileImage=/.../mstile-144x144.png`, `MobileOptimized=width`,
`HandheldFriendly=true`, `http-equiv=Content-Language de-DE`, `og:site_name`, `og:url`, `og:title`,
`og:description`, `og:image` + `og:image:url` + `og:image:secure_url` + `og:image:alt`, `og:locale=de_DE`,
`twitter:card=summary_large_image`, `twitter:site`, `twitter:creator`, `twitter:title`,
`twitter:description`, `twitter:image`, `twitter:image:alt`.

Links: `canonical`, `manifest`, `icon` (ico + png 16/32/96/160/196), `apple-touch-icon`
57/60/72/76/114/120/144/152, 40+ `alternate hreflang` incl. `x-default`, `preload as=image` x16.
`html lang="de-DE"`. No JSON-LD on the homepage.

Note the OG title is English while the page is German: a localisation bug, not a pattern.
