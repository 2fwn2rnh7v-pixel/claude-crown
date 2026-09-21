# Patterns: the Tesla / Apple mechanics, framework-free

Every recipe here is vanilla HTML + CSS + a few lines of JS, derived from the measured values in
`tesla-measured.md` and `apple-measured.md`. Numbers in the code are the measured ones; change them
on purpose, not by habit. React / Next.js / TanStack Start adapters are at the end.

Support baseline used below (checked 2026-09-21, caniuse): CSS scroll-driven animations
(`animation-timeline`) Chrome/Edge 115+, Safari 26+, Firefox 159+, 87% global. Use them behind
`@supports` with an IntersectionObserver fallback; never as the only path.

---

## 0. Tokens: one file, every number named

```css
:root {
  /* colour: cool greys stepped 10..70, one accent, nothing else */
  --ink-10: #171a20;  --ink-20: #393c41;  --ink-30: #5c5e62;  --ink-40: #a2a3a5;
  --ink-50: #d0d1d2;  --ink-60: #e2e3e3;  --ink-70: #f4f4f4;  --paper: #fff;
  --accent: #3e6ae1;  --accent-hover: #3457b1;
  --scrim-black: linear-gradient(to top, rgba(0,0,0,.6), rgba(0,0,0,0) 60%);

  /* space: 4px base, doubling */
  --s-half: 4px; --s-1: 8px; --s-2: 16px; --s-3: 24px; --s-4: 32px; --s-6: 48px; --s-8: 64px;
  --gutter: var(--s-3);            /* 24 phone */
  --radius: 4px;                   /* Tesla: 4 buttons, 8 cards. Apple: 980 pills, 18-30 cards */
  --radius-card: 8px;

  /* type: two families, two weights. "Universal Sans" is Tesla's licensed face, "SF Pro" is Apple's;
     put the project's own display + text faces here (self-hosted woff2, weights 400 + 500 only) */
  --font-text: "Universal Sans Text", system-ui, -apple-system, Arial, sans-serif;
  --font-display: "Universal Sans Display", var(--font-text);
  --fs-body: 14px; --lh-body: 20px;
  --fs-h1: 40px; --lh-h1: 48px;    /* phone */

  /* motion: one duration, one easing, one reveal easing */
  --t: .33s;
  --ease: cubic-bezier(.5, 0, 0, .75);
  --ease-reveal: cubic-bezier(.165, .84, .44, 1);
}
@media (min-width: 900px) {
  :root { --gutter: var(--s-6); --fs-h1: 56px; --lh-h1: 56px; }
}
```

Breakpoints, fixed for the whole project: **600 / 900 / 1200**. Add `(hover: hover)` and
`(prefers-reduced-motion: reduce)`; nothing else.

---

## 1. Page skeleton and the two things that break SSR

```html
<!doctype html>
<html lang="de">
<head> …see head-meta.md… </head>
<body>
  <a class="skip" href="#main">Zum Inhalt springen</a>
  <header class="nav" data-nav>…</header>
  <main id="main">
    <section class="hero">…</section>
    <section class="rail">…</section>
    <section class="grid">…</section>
  </main>
  <footer>…</footer>
  <div class="cta-bar" data-cta-bar>…</div>
</body>
</html>
```

- `html { scroll-behavior: smooth }` only inside `@media (prefers-reduced-motion: no-preference)`.
- Never `height: 100vh`. Use `100dvh` or, better, size sections by content / image aspect (see 3).
- Any JS that touches `window`, `document`, `matchMedia` runs after `DOMContentLoaded` (vanilla) or
  inside `useEffect` (React). Not at module top level.

---

## 2. Nav

### 2a. Tesla: 56px, white on desktop, transparent over the hero on phone

```css
.nav { height: 56px; display: flex; align-items: center; padding-inline: var(--gutter);
  color: #fff; background: transparent; transition: background-color var(--t), box-shadow var(--t), color var(--t); }
.nav__logo { height: 24px; width: auto; }               /* 120x24 measured */
.nav__items { display: none; }
.nav__menu { height: 32px; padding: 4px 16px; border-radius: var(--radius); font: 500 14px/20px var(--font-text);
  color: #fff; background: rgba(0,0,0,.05); backdrop-filter: blur(16px); border: 0; }

@media (min-width: 900px) {
  .nav { position: sticky; top: 0; z-index: 500; color: var(--ink-10); background: var(--paper); }
  .nav__menu { display: none; }
  .nav__items { display: flex; gap: 0; }
  .nav__item { padding: 4px 16px; border-radius: var(--radius); font: 500 14px/20px var(--font-text);
    color: var(--ink-10); transition: color var(--t), background-color var(--t); }
  @media (hover: hover) { .nav__item:hover { background: rgba(0,0,0,.05); } }
}
```

Phone: the header sits **over** the hero image (transparent), scrolls away with it. Desktop: white,
sticky. Mobile menu = full-screen white sheet with back arrow, title, close; not a slide-in drawer
from the side.

### 2b. Apple: 44-48px glass bar, always fixed

```css
.nav--glass { position: fixed; inset: 0 0 auto 0; height: 48px; z-index: 9999;
  background: rgba(255,255,255,.8); backdrop-filter: saturate(1.8) blur(20px); }
.nav--glass > .row { max-width: 1024px; margin-inline: auto; padding-inline: 22px; height: 100%; display: flex; align-items: center; }
body { padding-top: 48px; }                                /* reserve the bar, no overlap on the hero */
@media (prefers-reduced-transparency: reduce) { .nav--glass { background: #fafafc; backdrop-filter: none; } }
```

Do not write `-webkit-backdrop-filter` by hand in a Lightning CSS / Tailwind v4 build: the build
prefixes it, a handwritten one kills the standard property.

---

## 3. Hero: sized by the image, copy at the top, two CTAs

Tesla's hero is not `100vh`. Its height **is the image's aspect ratio** on phone
(767x1404 → `aspect-ratio: 767 / 1404`) and a fixed 660px on desktop. That is why nothing jumps
when the URL bar collapses and why the car is never cropped.

```html
<section class="hero">
  <picture class="hero__media">
    <source media="(max-width: 599px) and (orientation: portrait)"   srcset="/img/hero-mobile.jpg">
    <source media="(min-width: 600px) and (orientation: portrait)"   srcset="/img/hero-tablet.jpg">
    <source media="(min-width: 900px), (orientation: landscape)"     srcset="/img/hero-desktop.jpg">
    <img src="/img/hero-desktop.jpg" alt="Nordwind Modell E vor der Küste" width="3370" height="1430" fetchpriority="high" decoding="async">
  </picture>
  <div class="hero__copy">
    <h1>Modell E</h1>
    <p class="hero__sub">Ab 0 % Zinsen erhältlich</p>
    <div class="cta-row">
      <a class="btn btn--primary" href="/bestellen">Bestellen</a>
      <a class="btn btn--white"   href="/probefahrt">Probefahrt</a>
    </div>
  </div>
</section>
```

```css
.hero { position: relative; display: grid; grid-template-columns: minmax(0, 1fr); overflow: clip; isolation: isolate; }
/* overflow: clip (Apple tiles carry it) stops the 1px grid-rounding bleed that puts a horizontal scrollbar on phones */
.hero__media, .hero__media img { grid-area: 1 / 1; width: 100%; height: 100%; object-fit: cover; object-position: 50% 50%; }
.hero { aspect-ratio: 767 / 1404; max-height: 100dvh; }              /* phone: image decides */
@media (min-width: 600px) { .hero { aspect-ratio: auto; height: 660px; } }   /* tablet+desktop: fixed, measured */
.hero__copy { grid-area: 1 / 1; z-index: 1; display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: 64px var(--gutter) var(--s-3); color: #fff; }
.hero h1 { font: 500 var(--fs-h1)/var(--lh-h1) var(--font-display); margin: 0; }
.hero__sub { font: 400 20px/28px var(--font-display); margin: 4px 0 0; }
.cta-row { display: flex; gap: var(--s-1); margin-top: var(--s-4); width: min(100%, 408px); }
.cta-row .btn { flex: 1 1 0; }                                          /* 2-up on phone: 159.5 + 8 + 159.5 */
@media (min-width: 600px) { .cta-row .btn { flex: 0 0 200px; } }         /* desktop: 200px each */
```

Copy sits at the **top** of the image on Tesla (car stays visible below), at the **bottom-left**
on the product cards (`padding: 40px`, scrim). Pick one per block, never both.

Hero stack: headline, one subline, one footnote line max, two CTAs. Nothing else in the hero.

---

## 4. Buttons: one variable, swapped on state

The whole Tesla and Apple hover system is: paint from a custom property, change the property on
`:hover`, guard with `(hover: hover)`. No transform, no shadow growth, no glow.

```css
.btn {
  --bg: var(--accent); --fg: #fff; --bg-hover: var(--accent-hover); --fg-hover: var(--fg);
  display: inline-flex; align-items: center; justify-content: center;
  height: 40px; min-width: 160px; padding: 4px 24px; border-radius: var(--radius);
  border: 2px solid transparent; background: var(--bg); color: var(--fg);
  font: 500 14px/1.2 var(--font-text); text-decoration: none; white-space: nowrap; cursor: pointer;
  transition: background-color var(--t), color var(--t), border-color var(--t), box-shadow .25s;
}
.btn--white     { --bg: #fff; --fg: var(--ink-20); --bg-hover: #eee; }
.btn--secondary { --bg: transparent; --fg: var(--ink-10); --bg-hover: var(--ink-10); --fg-hover: #fff; border-color: currentColor; }
.btn--pill      { border-radius: 980px; height: auto; padding: 11px 21px; font-size: 17px; letter-spacing: -.022em; }  /* Apple */

@media (hover: hover) {
  .btn:hover { background: var(--bg-hover); color: var(--fg-hover); border-color: transparent; }
}
.btn:active        { background: color-mix(in srgb, var(--bg-hover), #000 4%); }   /* Apple: one step darker than hover */
.btn:focus-visible { outline: 2px solid #8e8e8e; outline-offset: 2px; }
.btn[disabled], .btn[aria-disabled="true"] { opacity: .42; pointer-events: none; }
```

Checks before shipping a button:
- Text fits on one line at every width. Tesla's phone "Weitere Informationen" wraps in 159px;
  shorten the label or let the button grow, never ship the wrap.
- Contrast: `#3e6ae1` on white text = 4.6:1, passes AA. `#eee` hover on `#393c41` text = 9:1.
- Ghost buttons over photos need a scrim or a backdrop (`.icon-btn` below), never bare.

Glass icon button (carousel arrows, mobile menu trigger):

```css
.icon-btn { width: 40px; height: 40px; border-radius: var(--radius); border: 0; display: grid; place-items: center;
  background: rgba(255,255,255,.75); backdrop-filter: blur(4px); box-shadow: 0 4px 4px rgba(0,0,0,.25);
  transition: background-color var(--t), transform var(--t) var(--ease); }
@media (hover: hover) { .icon-btn:hover { background: rgba(255,255,255,.9); } }
```

---

## 5. Reveal on enter (the only scroll effect Tesla uses)

30px travel, 500ms, `cubic-bezier(.165,.84,.44,1)`, once. Not 100px, not 1s, not on every element.
Apply to a section's copy block, at most one reveal group per section.

CSS-first (scroll-driven animation), with the observer as fallback:

```css
@media (prefers-reduced-motion: no-preference) {
  .reveal { opacity: 0; transform: translate3d(0, 30px, 0);
    transition: opacity .5s var(--ease-reveal), transform .5s var(--ease-reveal); }
  .reveal.is-in { opacity: 1; transform: none; }

  @supports (animation-timeline: view()) {
    .reveal { transition: none; animation: reveal linear both; animation-timeline: view(); animation-range: entry 0% entry 40%; }
    .reveal.is-in { animation: reveal linear both; }   /* keep the class harmless */
    @keyframes reveal { from { opacity: 0; transform: translate3d(0, 30px, 0); } to { opacity: 1; transform: none; } }
  }
}
```

```js
// fallback + the class hook; runs only where animation-timeline is missing
if (!CSS.supports('animation-timeline: view()') && matchMedia('(prefers-reduced-motion: no-preference)').matches) {
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target); }
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.2 });
  document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
}
```

Rules: no `window.addEventListener('scroll')` for reveals; the element is visible in a full-page
screenshot after the animation (never `opacity: 0` left behind if JS fails: the `@media` guard
above only applies when motion is allowed, and the fallback removes the class swap risk by
observing on load).

Staggered children (Apple `StaggeredFadeIn`): same keyframes, `transition-delay: calc(var(--i) * 60ms)`
with `--i` set inline per child. Cap at 6 children.

---

## 6. Horizontal rail with peek (Tesla product carousel)

Native scroll-snap, no library. The next card peeks in from the right; arrows and dots are sugar.

```html
<section class="rail" aria-roledescription="Karussell">
  <div class="rail__track" data-rail>
    <article class="card card--dark" style="--img: url(/img/card-1.jpg)">…</article>
    <article class="card card--dark" style="--img: url(/img/card-2.jpg)">…</article>
  </div>
  <div class="rail__dots" role="tablist" data-rail-dots></div>
</section>
```

```css
.rail__track { display: flex; gap: var(--s-3); overflow-x: auto; scroll-snap-type: x mandatory;
  scroll-padding-inline: var(--gutter); padding-inline: var(--gutter); scrollbar-width: none; scroll-behavior: smooth; }
.rail__track::-webkit-scrollbar { display: none; }
.card { flex: 0 0 min(1024px, calc(100% - var(--gutter)));            /* 1024 desktop, 330 on a 390 phone */
  height: 580px; scroll-snap-align: start; border-radius: var(--radius-card); overflow: hidden; position: relative; }
@media (max-width: 599px) { .card { height: 520px; } }
.card--dark::before { content: ""; position: absolute; inset: 0; background: var(--img) center / cover no-repeat; }
.card--dark::after  { content: ""; position: absolute; inset: 0; background: var(--scrim-black); }
.card__copy { position: absolute; inset: auto 0 0 0; z-index: 1; padding: 40px; color: #eee; }
.card__copy h2 { font: 500 48px/56px var(--font-display); color: #fff; margin: 0; }
.rail__dots { display: flex; justify-content: center; gap: 8px; margin-top: var(--s-3); }
.rail__dots button { width: 12px; height: 12px; border-radius: 8px; border: 0; background: var(--ink-10); opacity: .5; }
.rail__dots button[aria-selected="true"] { opacity: 1; }
```

```js
const track = document.querySelector('[data-rail]');
const dots = document.querySelector('[data-rail-dots]');
const cards = [...track.children];
cards.forEach((c, i) => { const b = document.createElement('button'); b.role = 'tab'; b.ariaLabel = `Karte ${i + 1}`;
  b.onclick = () => c.scrollIntoView({ inline: 'start', block: 'nearest', behavior: 'smooth' }); dots.append(b); });
new IntersectionObserver((es) => es.forEach((e) => {                     // active dot = the card >= 60% visible
  if (e.isIntersecting) dots.children[cards.indexOf(e.target)].ariaSelected = 'true';
  else dots.children[cards.indexOf(e.target)].ariaSelected = 'false'; }), { root: track, threshold: .6 })
  .observe?.(cards[0]); cards.forEach((c) => io.observe(c));
```

(Keep the observer in one variable; the snippet is shortened. No scroll listener.)

---

## 7. Grey card grid with a bleeding product shot

```css
.grid { display: grid; gap: var(--s-3); padding-inline: var(--gutter); }
@media (min-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
.tile { background: var(--ink-70); border-radius: var(--radius-card); overflow: hidden; display: grid; min-height: 292px; }
.tile__copy { padding: var(--s-6) var(--s-6) var(--s-4); align-self: center; }
.tile h2 { font: 500 34px/44px var(--font-display); color: var(--ink-10); margin: 0 0 8px; }
.tile p  { font: 400 17px/24px var(--font-text); color: var(--ink-20); max-width: 40ch; margin: 0 0 var(--s-3); }
.tile img { width: 100%; height: 100%; object-fit: cover; }
@media (min-width: 900px) { .tile { grid-template-columns: 1.4fr 1fr; } .tile img { object-fit: contain; object-position: right center; transform: scale(1.35) translateX(10%); } }
```

Two tiles, not three. Each tile has an image; a grey box with only text is the AI tell.

---

## 8. Sticky scrub section (Apple product pages)

The parent gives scroll room (2 to 3 viewports), the child stays pinned for exactly that room,
and one number (progress 0..1) drives everything inside. Apple resolves this with a JS keyframe
engine; the CSS timeline does the same thing in one line where supported.

```html
<section class="scrub" style="--vh: 2.2">
  <div class="scrub__pin">
    <picture class="scrub__frame scrub__frame--start">…</picture>
    <video class="scrub__video" muted playsinline preload="none" data-src="/vid/camera.mp4"></video>
    <picture class="scrub__frame scrub__frame--end">…</picture>
    <div class="scrub__copy reveal"><h2>Die Kamera, neu gedacht.</h2></div>
  </div>
</section>
```

```css
.scrub { height: calc(var(--vh) * 100dvh); }
.scrub__pin { position: sticky; top: 0; height: 100dvh; overflow: clip; display: grid; }
.scrub__pin > * { grid-area: 1 / 1; }
.scrub__frame img, .scrub__video { width: 100%; height: 100%; object-fit: cover; }
.scrub__frame--end { opacity: 0; }

@supports (animation-timeline: scroll()) {
  @media (prefers-reduced-motion: no-preference) {
    .scrub { view-timeline: --scrub block; }
    .scrub__copy { animation: copy-in linear both; animation-timeline: --scrub; animation-range: 30% 60%; }
    @keyframes copy-in { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: none; } }
  }
}
```

```js
// progress for JS-driven things (video.currentTime, a counter), once, rAF-coalesced
function scrubProgress(section, onProgress) {
  let ticking = false;
  const read = () => { const r = section.getBoundingClientRect();
    const p = Math.min(1, Math.max(0, -r.top / (r.height - innerHeight))); onProgress(p); ticking = false; };
  const io = new IntersectionObserver(([e]) => {
    if (e.isIntersecting) addEventListener('scroll', tick, { passive: true }); else removeEventListener('scroll', tick); });
  const tick = () => { if (!ticking) { ticking = true; requestAnimationFrame(read); } };
  io.observe(section); read();
}
```

The listener exists only while the section is on screen and only schedules one frame; that is the
allowed shape of a scroll listener. Everything drawn is a function of `p`; nothing runs on a clock.

Video inside the pin (Apple's start-frame / end-frame pair):

```js
const v = section.querySelector('.scrub__video');
new IntersectionObserver(([e]) => {
  if (e.isIntersecting && !v.src) { v.src = v.dataset.src; v.play().catch(() => {}); }
}, { threshold: .5 }).observe(section);
v.addEventListener('ended', () => section.querySelector('.scrub__frame--end').style.opacity = 1);
if (matchMedia('(prefers-reduced-motion: reduce)').matches) { v.remove(); section.querySelector('.scrub__frame--end').style.opacity = 1; }
```

Start frame under the video = no black flash. End frame after `ended` = no player UI, no loop.
Reduced motion = the end frame only. For scroll-scrubbed video (`currentTime` from `p`), encode
with a small GOP (`-g 8`), strip audio, `faststart`, and load via Blob; see the `scroll-world` skill.

---

## 9. Persistent CTA bar

```css
.cta-bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 10; display: flex; justify-content: center;
  padding: 14px var(--gutter) calc(14px + env(safe-area-inset-bottom)); background: #fff;
  box-shadow: 0 -1px 0 var(--ink-60); transform: translateY(100%);
  transition: transform .3s ease-in-out, box-shadow .3s ease-in-out; }
.cta-bar.is-visible { transform: none; }
.cta-bar .btn { --bg: var(--ink-70); --fg: var(--ink-20); --bg-hover: var(--ink-60); border: 1px solid var(--ink-50); gap: 10px; width: 100%; max-width: 321px; }
@media (min-width: 900px) { .cta-bar { background: transparent; box-shadow: none; padding-block: 10px; } .cta-bar .btn { width: 236px; } }
```

```js
// show after the hero has left, hide again near the footer; one observer, no scroll math
const bar = document.querySelector('[data-cta-bar]');
new IntersectionObserver(([e]) => bar.classList.toggle('is-visible', !e.isIntersecting), { threshold: .1 })
  .observe(document.querySelector('.hero'));
```

Requires `viewport-fit=cover` in the meta viewport for the safe-area inset to exist.

---

## 10. Images: art direction, density, reservation

Priority order, from what the two sites actually do:

1. **One file per device, not one file scaled.** Hero and cards are `<picture>` with 3 to 5
   `<source media>` crops (phone portrait, tablet portrait, landscape/desktop; Apple adds
   `min-height` variants). The phone crop is a different composition, not a centre crop.
2. **1x/2x per crop** (`srcset="a.jpg, a_2x.jpg 2x"`) or a CDN transform that negotiates format
   and quality (`f_auto,q_auto`). Serve at about 2x the rendered box, never 4x.
3. **Reserve the box**: `width`/`height` attributes on `<img>` or `aspect-ratio` on the wrapper.
   CLS comes from images without a reserved box.
4. **Hero eager, everything below lazy**: hero `<img fetchpriority="high">`, the rest
   `loading="lazy" decoding="async"`.
5. **Preload what opens instantly**: menu thumbnails as `<link rel="preload" as="image">` (Tesla
   preloads 16), the hero's chosen crop with `imagesrcset`/`imagesizes` when it is the LCP.
6. **Object-fit**: `cover` for photos, `contain` for cut-out product renders, and set
   `object-position` on purpose when the subject is off-centre in one crop.
7. **Format**: WebP/AVIF via the CDN or a build step; PNG only for cut-outs that need alpha.

Anti-slop: no placeholder gradients where a photo belongs, no `div` "screenshots", no image
without `alt` (empty `alt=""` for decorative art, a real sentence for product shots).

---

## 11. Reduced motion, contrast, focus

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
  .reveal { opacity: 1; transform: none; }
  .scrub__video { display: none; } .scrub__frame--end { opacity: 1; }
}
```

Every animated element has a static end state that a full-page screenshot shows. Every
interactive element has `:focus-visible`. Text on photos gets a scrim (`--scrim-black`) or sits on
the sky, never on the detail.

---

## 12. Framework adapters

The recipes above are the source of truth; the adapters only say where the same code lives.

### React (Next.js App Router, TanStack Start, Vite)

- Anything that uses `IntersectionObserver`, `matchMedia`, `window`, `requestAnimationFrame` is a
  **client leaf**: `'use client'` at the top (Next), or a component only rendered after mount
  (TanStack: `useEffect` + `useState` gate). Never at module scope: SSR renders it.
- One hook, reused:

```tsx
// use-in-view.ts
import { useEffect, useRef, useState } from 'react';
export function useInView<T extends HTMLElement>(opts: IntersectionObserverInit = { threshold: 0.2 }) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setInView(true); io.disconnect(); } }, opts);
    io.observe(el);
    return () => io.disconnect();          // cleanup, always
  }, []);
  return { ref, inView };
}
```

  Use it for `.reveal` (`className={inView ? 'reveal is-in' : 'reveal'}`), the CTA bar, video play.
  Keep the CSS exactly as in section 5; the hook only toggles the class.
- Scroll progress (section 8): keep `scrubProgress` as is inside `useEffect`, return its teardown.
  Do not store progress in `useState` (re-render per frame); write to a CSS variable
  (`el.style.setProperty('--p', p)`) or a `ref`.
- GSAP / Lenis / Motion only via dynamic import inside the client leaf; they are not needed for
  anything in this file.
- Images: `next/image` with `sizes` and `priority` on the hero; for art direction use a plain
  `<picture>` with `<source media>` and `next/image` on the `<img>`, or the `getImageProps` helper.
  TanStack Start on Cloudflare: plain `<picture>` + pre-generated crops in `public/`.

### Tailwind v4

Tokens from section 0 become `@theme` variables; every recipe maps 1:1 (`h-10 rounded px-6` for the
button). Hover: `hover:bg-[--bg-hover]` is fine, but keep the `(hover: hover)` guard with a
`@custom-variant hover (&:hover)` override or the `hover:` variant in v4 (which is already
`@media (hover: hover)`-gated). Do not write `-webkit-backdrop-filter`.

### Plain server templates (Drupal, Rails, Django, PHP)

Ship the CSS + the three JS snippets (reveal, rail dots, CTA bar) as one deferred module. Tesla
runs exactly this shape on Drupal 10.
