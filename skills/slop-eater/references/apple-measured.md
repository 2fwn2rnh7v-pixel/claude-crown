# Apple.com, measured (short pass)

Measured 2026-09-21 on `https://www.apple.com/de/` and `https://www.apple.com/de/iphone-18-pro/`,
playwright-cli, real Chrome, 1440x900. Only the parts Tesla does not show: the glass nav, pill
buttons, the tile system, and how the scroll-driven product pages are actually built.

## Nav (`.globalnav`)

```
position fixed; top 0; height 44px (token --r-globalnav-height 48px on product pages); z-index 9999
background rgba(255,255,255,.8); backdrop-filter saturate(1.8) blur(20px)
inner .globalnav-content: max-width 1024px; padding 0 22px; background transparent
first nav link measured: 17px / 600, color rgba(0,0,0,.8), letter-spacing -0.374px, padding 0 8px
(that element sits in the flyout; the bar labels render smaller, re-measure per element)
opened menu background: #fafafc light / #161617 dark
```

The blur is on the bar, the max-width is on the inner row. On product pages a second bar
(`#ac-localnav`, 52px, `position: sticky` via `.css-sticky`) carries the product name + buy CTA.

## Type

`"SF Pro Text"` body 17px / 25px, `letter-spacing: -0.374px` (Apple tracks negatively at every
size: -0.022em), colour `#1d1d1f`. Headlines `"SF Pro Display"` 56px / 60px / 600,
`letter-spacing: -0.28px`; tile headline 40px / 44px / 600. Off-white text on dark tiles `#f5f5f7`.

## Buttons (`.button`)

```
border-radius 980px          (pill; any huge number)
padding 11px 21px            (reduced variant: 4px 11px, 12px font)
font 17px / 20px / 400; letter-spacing -0.374px
min-width 26px; border 0.8px solid transparent; rendered 143.95 x 43.6
background var(--sk-button-background)
```

Variables per variant, swapped on state (the whole hover system is CSS custom properties):

| Variant | background | hover | active | text |
|---|---|---|---|---|
| `.button` | `#0071e3` | `#0076df` | `#006edb` | white |
| `.button-secondary` (light) | transparent, border `#0066cc` | `#0076df`, border transparent | `#006edb` | `#0066cc` → white |
| `.button-secondary` (dark) | transparent, border `#2997ff` | `#0076df` | `#006edb` | `#2997ff` → white |

```css
.button:hover  { background: var(--sk-button-background-hover, var(--sk-button-background));
                 color: var(--sk-button-color-hover, var(--sk-button-color));
                 text-decoration: none; border-color: transparent; }
.button:active { background: var(--sk-button-background-active, ...); outline: none; }
.button:focus-visible { outline: 2px solid var(--sk-focus-color, #0071e3); outline-offset: 3px; }
```

Hover moves the colour by ~2% lightness. No transform, no shadow. `--sk-button-disabled-opacity: .42`.

## Breakpoints (three widths, plus height)

```
(max-width: 734px)      small
(max-width: 1068px)     medium
(min-width: 1069px)     large
(min-width: 1441px)     xlarge
(min-height: 776px) / (max-height: 775px)  tall vs short, combined with width
```

Height queries are how Apple picks `largetall` vs `large` assets for the same width.

## Homepage tiles

`section.section-hero` is 2100px tall = three `.tile-wrapper` at **692px each**
(`position: relative; overflow: clip`), themed `theme-dark` / light per tile. Not 100vh; fixed
heights per breakpoint. Each tile = startframe `<picture>` + a `<video>`:

```html
<picture>
  <source media="(max-width:734px)"                              srcset="..._small.jpg, ..._small_2x.jpg 2x">
  <source media="(max-width:1068px) and (min-height:734px)"      srcset="..._mediumtall.jpg, ..._mediumtall_2x.jpg 2x">
  <source media="(max-width:1068px) and (max-height:733px)"      srcset="..._medium.jpg, ..._medium_2x.jpg 2x">
  <source media="(min-width:0px) and (min-height:776px)"         srcset="..._largetall.jpg, ..._largetall_2x.jpg 2x">
  <source media="(min-width:0px) and (max-height:775px)"         srcset="..._large.jpg, ..._large_2x.jpg 2x">
  <img src="..._largetall.jpg" alt="">
</picture>
<video muted playsinline preload="none" data-inline-media data-inline-media-basepath="...">
```

Five art-directed crops x 1x/2x. Video: `muted playsinline preload="none"`, **no `autoplay`
attribute**; JS (`ac-films` / inline-media) sets the source per breakpoint and plays it when the
tile is in view, then unloads at end (`data-inline-media-unload-at-end`). Poster = the startframe
picture underneath, so nothing flashes.

## Product page: how the scroll-driven sections are built

`iphone-18-pro` overview: 30537px tall, **14 `<video>`, 0 `<canvas>`, 0 CSS `animation-timeline`**.
Apple's "scroll animation" today is JS keyframes over sticky containers, not canvas frame
sequences and not CSS scroll-driven animations.

```
section[data-anim-scroll-group="Pro Video"]        <- one scroll group
  .scroll-container.sticky-true  height 1980px      <- 2.2x viewport of scroll room
    .sticky-container  position sticky; top 0; height 901px (= 100vh)
      .media-container                               <- what the user sees while the parent scrolls
  div[data-anim-keyframe-1='{"start": "a0t - 100vh + css(--global-section-padding)",
                              "end": "a1t - 100vh", "anchors": [".section-pro-video", ...]}']
```

Keyframe boundaries are expressed relative to anchor elements (`a0t` = anchor 0 top) and the
viewport, resolved once per resize; the engine maps `scrollY` to progress 0..1 and sets
transforms/opacity. 30 `will-change` rules. Sections also carry
`data-component-list="StaggeredFadeIn"` (children fade in with a stagger when the section enters),
`data-deep-link`, and `data-analytics-section-engagement`.

Video sections use a **start frame / end frame pair**:

```
picture.overview-media-hero-hero-startframe.pin-offset.start-frame   shown before play
video (preload=none, muted, playsinline)                              plays once in view
picture.overview-media-hero-hero-endframe.pin-offset.end-frame       holds the last frame after
picture...endframe.fallback-frame                                    reduced-motion / failed load
```

That pair is what makes a video feel like part of the page instead of a player: the page never
shows black, and reduced-motion users get the end frame as a still.

Galleries: `data-scroll-gallery`, `data-staggered-anchor`, `CaptionTileGallery` = horizontal
scroll-snap tiles with captions, same idea as Tesla's carousel.

## Meta

`viewport=width=device-width, initial-scale=1, viewport-fit=cover`, `og:type=website`,
`og:locale=de_DE`, `og:image` (a generic logo card, 1200x630), `og:site_name`. Focus colour token
`--sk-focus-color: #0071e3`. `(prefers-reduced-motion)` x4, `(prefers-contrast: more)` x1,
`(inverted-colors)` x3 in the CSS.
