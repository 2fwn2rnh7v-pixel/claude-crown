#!/usr/bin/env python3
"""slop_scan.py: find the mechanical AI-slop tells on a marketing page.

Compares HTML/CSS/JS/TS/TSX/JSX/Vue/Astro files against the measured Tesla.com / Apple.com
standard (see ../references/*.md). Stdlib only. A hit is a lead, not a verdict: confirm at the
element before it becomes a finding.

Usage:
    python slop_scan.py <file-or-dir> [more paths] [--json] [--fail-on CRITICAL|HIGH|MEDIUM|LOW]

Exit code 1 when any finding is at or above --fail-on (default: never fails).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

EXTS = {".html", ".htm", ".css", ".scss", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".vue", ".astro", ".svelte"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".output", ".vercel", "coverage", ".playwright-cli", "vendor"}
LEVELS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


@dataclass
class Hit:
    severity: str
    code: str
    file: str
    line: int
    message: str
    excerpt: str = ""


def iter_files(paths: list[str]):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for root, dirs, files in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if os.path.splitext(f)[1].lower() in EXTS:
                    yield os.path.join(root, f)


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def excerpt_at(text: str, idx: int, width: int = 90) -> str:
    start = text.rfind("\n", 0, idx) + 1
    end = text.find("\n", idx)
    end = len(text) if end == -1 else end
    return text[start:end].strip()[:width]


def strip_comments_css(css: str) -> str:
    return re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), css, flags=re.S)


def css_rules(css: str):
    """Yield (selector, body, start_index) for top-level and nested rules. Good enough for audits."""
    css = strip_comments_css(css)
    depth = 0
    sel_start = 0
    stack: list[tuple[str, int, int]] = []
    i = 0
    n = len(css)
    while i < n:
        c = css[i]
        if c == "{":
            selector = css[sel_start:i].strip()
            stack.append((selector, i + 1, sel_start))
            depth += 1
            sel_start = i + 1
        elif c == "}":
            if stack:
                selector, body_start, s0 = stack.pop()
                yield selector, css[body_start:i], s0
            depth -= 1
            sel_start = i + 1
        elif c == ";" and depth == 0:
            sel_start = i + 1
        i += 1


def scan_css(text: str, file: str, hits: list[Hit], ctx: dict):
    ctx["has_motion"] |= bool(re.search(r"\b(animation|transition)\s*:", text))
    ctx["has_reduced_motion"] |= "prefers-reduced-motion" in text
    ctx["has_hover"] |= ":hover" in text
    ctx["has_hover_guard"] |= bool(re.search(r"\(\s*hover\s*:\s*hover\s*\)", text))
    ctx["has_focus_visible"] |= ":focus-visible" in text

    for m in re.finditer(r"@media[^{]*?\(\s*(?:min|max)-width\s*:\s*(\d+(?:\.\d+)?)(px|em|rem)", text):
        val = m.group(1) + m.group(2)
        ctx["breakpoints"].setdefault(val, (file, line_of(text, m.start())))

    for selector, body, start in css_rules(text):
        if selector.startswith("@"):
            continue
        sel_l = selector.lower()
        body_l = body.lower()
        ln = line_of(text, start)

        if re.search(r"(?<!max-)\b(?:min-)?height\s*:\s*100\s*(?:vh|svh|lvh)\b", body_l):
            sev = "CRITICAL" if re.search(r"hero|banner|intro|landing", sel_l) else "HIGH"
            hits.append(Hit(sev, "VH_HERO", file, ln,
                            "Viewport-height section. Tesla: hero 660px desktop / image aspect on phone; Apple tiles 692px. "
                            "Use aspect-ratio from the phone crop + fixed px from 600px, or 100dvh only for a sticky pin.",
                            selector[:80]))
        elif re.search(r"(?<!max-)\b(?:min-)?height\s*:\s*100\s*dvh\b", body_l) and not re.search(r"pin|sticky|scrub|(^|,)\s*(html|body|#root|#app|\.app|main)\s*($|,)", sel_l):
            hits.append(Hit("LOW", "DVH_SECTION", file, ln,
                            "100dvh outside a sticky pin. Acceptable only for the pinned child of a scrub section.",
                            selector[:80]))

        if ":hover" in sel_l:
            moved = re.search(r"\btransform\s*:\s*(?!none)|\bscale\s*:|\btranslate\s*:|\brotate\s*:", body_l)
            shadow = re.search(r"\bbox-shadow\s*:\s*(?!none|inset\s+0\s+0\s+0)", body_l) or "drop-shadow" in body_l
            glow = re.search(r"\bfilter\s*:\s*(?!none)", body_l)
            if moved or shadow or glow:
                what = ", ".join(w for w, f in (("transform", moved), ("box-shadow", shadow), ("filter", glow)) if f)
                pseudo_fill = bool(moved) and not shadow and not glow and re.search(r"::?(after|before)", sel_l)
                hits.append(Hit("MEDIUM" if pseudo_fill else "HIGH", "HOVER_MOVE", file, ln,
                                f"Hover changes {what}. Tesla/Apple hover = one colour variable "
                                "(#3e6ae1->#3457b1, #fff->#eee, #0071e3->#0076df), no movement, no shadow, no glow."
                                + (" Pseudo-element fill: acceptable only if the button box itself stays put." if pseudo_fill else ""),
                                selector[:80]))
        if re.search(r"\banimation(?:-iteration-count)?\s*:[^;]*\binfinite\b", body_l):
            hits.append(Hit("MEDIUM", "INFINITE_ANIM", file, ln,
                            "Infinite animation. Nothing runs on a clock; the only measured infinite loop is a 2s "
                            "5px bounce on a down-arrow. Remove or tie to a state.", selector[:80]))
        if re.search(r"grid-template-columns\s*:\s*repeat\(\s*3\s*,", body_l):
            hits.append(Hit("MEDIUM", "THREE_CARDS", file, ln,
                            "Three equal columns. Tesla uses a 2-up tile grid and a horizontal rail; three identical "
                            "cards is the templated tell.", selector[:80]))
        if "-webkit-backdrop-filter" in body_l:
            hits.append(Hit("MEDIUM", "WEBKIT_BACKDROP", file, ln,
                            "Handwritten -webkit-backdrop-filter. Build tools (Lightning CSS, Tailwind v4) prefix it; "
                            "a handwritten copy can drop the standard property and flatten every glass surface.",
                            selector[:80]))
        if re.search(r"\bscroll-snap-type\s*:\s*[xy]?\s*(?:block|y)\b", body_l) and re.search(r"\b(html|body|main)\b", sel_l):
            hits.append(Hit("MEDIUM", "PAGE_SNAP", file, ln,
                            "Page-level scroll snap. Tesla's homepage container is literally named "
                            "'tcl-homepage-no-scroll-snapping'; snap only inside horizontal rails.", selector[:80]))


def strip_comments_js(js: str) -> str:
    """Blank out block and line comments, keeping newlines so line numbers stay correct."""
    js = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), js, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", lambda m: " " * len(m.group(0)), js)


def scan_js(text: str, file: str, hits: list[Hit]):
    text = strip_comments_js(text)
    for m in re.finditer(r"addEventListener\(\s*['\"]scroll['\"]|\bonscroll\s*=|window\.onscroll", text):
        ln = line_of(text, m.start())
        window = text[max(0, m.start() - 600): m.start() + 200]
        gated = "IntersectionObserver" in window and "requestAnimationFrame" in window
        sev = "LOW" if gated else "HIGH"
        hits.append(Hit(sev, "SCROLL_LISTENER", file, ln,
                        "Scroll listener. Allowed only inside an IntersectionObserver-gated section with rAF "
                        "coalescing (see patterns.md 8); for nav state, reveals and CTA bars use IntersectionObserver "
                        "or CSS animation-timeline." + (" (looks gated, verify)" if gated else ""),
                        excerpt_at(text, m.start())))
    scrolly = list(re.finditer(r"\b(?:window\.)?scrollY\b|\bpageYOffset\b", text))
    if scrolly and not any(h.code == "SCROLL_LISTENER" and h.file == file for h in hits):
        m = scrolly[0]
        hits.append(Hit("LOW", "SCROLLY_MATH", file, line_of(text, m.start()),
                        f"Reads scrollY ({len(scrolly)}x in this file) with no scroll listener nearby: fine inside one "
                        "rAF per frame; a lead if it feeds React state or per-element layout.", excerpt_at(text, m.start())))
    for m in re.finditer(r"\bparallax\b", text, flags=re.I):
        hits.append(Hit("MEDIUM", "PARALLAX", file, line_of(text, m.start()),
                        "Parallax. Tesla ships 'tcl-parallax-effect--off'; Apple pins and scrubs instead. Drop it or "
                        "make it a sticky scrub driven by one progress value.", excerpt_at(text, m.start())))


HEAD_CHECKS = [
    # (regex, severity, code, message)
    (r'<meta[^>]+name=["\']viewport["\']', "CRITICAL", "HEAD_VIEWPORT", "No viewport meta."),
    (r'<meta[^>]+name=["\']viewport["\'][^>]*viewport-fit=cover', "MEDIUM", "HEAD_VIEWPORT_FIT",
     "viewport-fit=cover missing: env(safe-area-inset-*) stays 0, the persistent CTA bar hides behind the home indicator."),
    (r'<link[^>]+rel=["\']canonical["\']', "CRITICAL", "HEAD_CANONICAL", "No canonical link."),
    (r'<meta[^>]+property=["\']og:image["\']', "CRITICAL", "HEAD_OG_IMAGE", "No og:image: shares render as a bare link."),
    (r'<meta[^>]+property=["\']og:image:alt["\']', "HIGH", "HEAD_OG_IMAGE_ALT", "No og:image:alt (Tesla and the OG spec carry it)."),
    (r'<meta[^>]+property=["\']og:title["\']', "HIGH", "HEAD_OG_TITLE", "No og:title."),
    (r'<meta[^>]+property=["\']og:description["\']', "HIGH", "HEAD_OG_DESC", "No og:description."),
    (r'<meta[^>]+name=["\']twitter:card["\']', "HIGH", "HEAD_TWITTER_CARD", "No twitter:card=summary_large_image."),
    (r'<meta[^>]+name=["\']twitter:image:alt["\']', "MEDIUM", "HEAD_TWITTER_ALT", "No twitter:image:alt."),
    (r'<link[^>]+rel=["\']manifest["\']', "HIGH", "HEAD_MANIFEST", "No web app manifest (Android icon, install, maskable icon)."),
    (r'<meta[^>]+name=["\']theme-color["\']', "HIGH", "HEAD_THEME_COLOR", "No theme-color (browser chrome tint)."),
    (r'<link[^>]+rel=["\']apple-touch-icon["\']', "HIGH", "HEAD_TOUCH_ICON", "No apple-touch-icon (iOS home screen)."),
    (r'<link[^>]+rel=["\']icon["\'][^>]+(?:type=["\']image/svg\+xml["\']|\.svg)', "MEDIUM", "HEAD_SVG_ICON", "No SVG favicon."),
    (r'<meta[^>]+name=["\']msapplication-TileColor["\']', "LOW", "HEAD_TILE", "No msapplication-TileColor/TileImage (Windows tile)."),
    (r'<meta[^>]+name=["\']description["\']', "HIGH", "HEAD_DESCRIPTION", "No meta description."),
    (r'<link[^>]+rel=["\']preload["\'][^>]+as=["\']image["\']', "MEDIUM", "HEAD_LCP_PRELOAD", "No image preload for the hero (LCP)."),
    (r'<html[^>]+lang=', "HIGH", "HEAD_LANG", "No lang attribute on <html>."),
]

DEAD_META = [
    (r'<meta[^>]+name=["\']keywords["\']', "META_KEYWORDS", "meta keywords: ignored by every engine since 2009."),
    (r'<meta[^>]+name=["\']author["\']', "META_AUTHOR", "meta author: no consumer."),
    (r'<meta[^>]+http-equiv=["\']X-UA-Compatible["\']', "META_XUA", "X-UA-Compatible: no IE left."),
    (r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']\s*index\s*,\s*follow', "META_ROBOTS", "robots index,follow is the default."),
    (r'<meta[^>]+name=["\'](?:HandheldFriendly|MobileOptimized)["\']', "META_HANDHELD", "HandheldFriendly/MobileOptimized: BlackBerry era."),
]


def strip_html_scripts(html: str) -> str:
    html = re.sub(r"<!--.*?-->", lambda m: " " * len(m.group(0)), html, flags=re.S)
    html = re.sub(r"<script\b.*?</script>", lambda m: " " * len(m.group(0)), html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", lambda m: " " * len(m.group(0)), html, flags=re.S | re.I)
    return html


def scan_html(text: str, file: str, hits: list[Hit], ctx: dict):
    head_m = re.search(r"<head\b.*?</head>", text, flags=re.S | re.I)
    if head_m:
        head = head_m.group(0)
        for rx, sev, code, msg in HEAD_CHECKS:
            if not re.search(rx, head, flags=re.I):
                hits.append(Hit(sev, code, file, line_of(text, head_m.start()), msg))
        for rx, code, msg in DEAD_META:
            m = re.search(rx, head, flags=re.I)
            if m:
                hits.append(Hit("LOW", code, file, line_of(text, head_m.start() + m.start()), msg, excerpt_at(text, head_m.start() + m.start())))
        if not re.search(r'<html[^>]+lang=', text[: head_m.start() + 10], flags=re.I):
            pass  # already covered by HEAD_LANG against the head slice; <html> sits before <head>
        # HEAD_LANG looks at head slice only; re-check the real <html> tag
        hits[:] = [h for h in hits if not (h.code == "HEAD_LANG" and re.search(r'<html[^>]+lang=', text, flags=re.I))]

    visible = strip_html_scripts(text)
    body_m = re.search(r"<body\b.*?</body>", visible, flags=re.S | re.I)
    body = body_m.group(0) if body_m else visible
    body_off = body_m.start() if body_m else 0
    # dashes in visible text (also title/meta content in head count as visible on share cards)
    for m in re.finditer(r"[—–]", visible):
        hits.append(Hit("MEDIUM", "DASH", file, line_of(text, m.start()),
                        "Em/en dash in visible text. Use a period, comma, colon or hyphen.", excerpt_at(text, m.start())))

    # images
    for m in re.finditer(r"<img\b[^>]*>", body, flags=re.I):
        tag = m.group(0)
        idx = body_off + m.start()
        ln = line_of(text, idx)
        src = re.search(r'\bsrc=["\']([^"\']*)', tag, flags=re.I)
        srcv = src.group(1) if src else ""
        if srcv.startswith("data:") or srcv.lower().endswith(".svg"):
            continue
        in_picture = re.search(r"<picture\b[^>]*>(?:(?!</picture>).)*$", body[max(0, m.start() - 2000): m.start()], flags=re.S | re.I)
        if not in_picture and not re.search(r"\bsrcset=", tag, flags=re.I):
            hits.append(Hit("HIGH", "IMG_ONE_FILE", file, ln,
                            "One image file for every device. Tesla: <picture> with 3-4 art-directed crops; Apple: 5 crops x 1x/2x.",
                            tag[:90]))
        has_size = re.search(r"\bwidth=", tag, flags=re.I) and re.search(r"\bheight=", tag, flags=re.I)
        if not has_size and not re.search(r"aspect-ratio", tag, flags=re.I):
            hits.append(Hit("HIGH", "IMG_NO_BOX", file, ln,
                            "No width/height (or aspect-ratio) reserved: layout shift when it loads.", tag[:90]))
        if not re.search(r'\balt=', tag, flags=re.I):
            hits.append(Hit("MEDIUM", "IMG_NO_ALT", file, ln, "No alt attribute (empty alt=\"\" for decorative art).", tag[:90]))
        if not re.search(r'\bloading=|\bfetchpriority=', tag, flags=re.I):
            hits.append(Hit("LOW", "IMG_NO_LOADING", file, ln,
                            "Neither loading=lazy nor fetchpriority=high: decide eager (hero) or lazy (below).", tag[:90]))

    # inline styles / scripts get scanned as CSS / JS too
    for m in re.finditer(r"<style\b[^>]*>(.*?)</style>", text, flags=re.S | re.I):
        sub_hits: list[Hit] = []
        scan_css(m.group(1), file, sub_hits, ctx)
        off = line_of(text, m.start(1)) - 1
        for h in sub_hits:
            h.line += off
        hits.extend(sub_hits)
    for m in re.finditer(r"<script\b[^>]*>(.*?)</script>", text, flags=re.S | re.I):
        sub_hits = []
        scan_js(m.group(1), file, sub_hits)
        off = line_of(text, m.start(1)) - 1
        for h in sub_hits:
            h.line += off
        hits.extend(sub_hits)

    # tailwind-style class tells
    for m in re.finditer(r'class(?:Name)?=["\'][^"\']*\b(?:min-)?h-screen\b', text):
        hits.append(Hit("CRITICAL", "VH_HERO", file, line_of(text, m.start()),
                        "h-screen / min-h-screen. Size by image aspect or fixed px; h-dvh only for a sticky pin.",
                        excerpt_at(text, m.start())))
    for m in re.finditer(r'class(?:Name)?=["\'][^"\']*\bhover:(?:scale|-?translate|shadow|drop-shadow)-', text):
        hits.append(Hit("HIGH", "HOVER_MOVE", file, line_of(text, m.start()),
                        "Tailwind hover with scale/translate/shadow. Hover = colour only.", excerpt_at(text, m.start())))
    for m in re.finditer(r'class(?:Name)?=["\'][^"\']*\b(?:md:|lg:)?grid-cols-3\b', text):
        hits.append(Hit("MEDIUM", "THREE_CARDS", file, line_of(text, m.start()),
                        "grid-cols-3: three equal cards is the templated tell.", excerpt_at(text, m.start())))


def scan(paths: list[str]) -> tuple[list[Hit], dict]:
    hits: list[Hit] = []
    ctx = {"has_motion": False, "has_reduced_motion": False, "has_hover": False, "has_hover_guard": False,
           "has_focus_visible": False, "breakpoints": {}, "files": 0}
    for f in iter_files(paths):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        ctx["files"] += 1
        ext = os.path.splitext(f)[1].lower()
        if ext in {".html", ".htm", ".vue", ".astro", ".svelte"}:
            scan_html(text, f, hits, ctx)
            if ext != ".html" and ext != ".htm":
                scan_js(text, f, hits)
        elif ext in {".css", ".scss"}:
            scan_css(text, f, hits, ctx)
        else:
            scan_js(text, f, hits)
            # JSX/TSX class tells
            for m in re.finditer(r'className=["\'`][^"\'`]*\b(?:min-)?h-screen\b', text):
                hits.append(Hit("CRITICAL", "VH_HERO", f, line_of(text, m.start()),
                                "h-screen / min-h-screen in JSX. Size by image aspect or fixed px.", excerpt_at(text, m.start())))
            for m in re.finditer(r'className=["\'`][^"\'`]*\bhover:(?:scale|-?translate|shadow|drop-shadow)-', text):
                hits.append(Hit("HIGH", "HOVER_MOVE", f, line_of(text, m.start()),
                                "Tailwind hover with scale/translate/shadow. Hover = colour only.", excerpt_at(text, m.start())))
            for m in re.finditer(r"transform\s*:\s*[`'\"]?\s*(?:scale|translate)", text):
                if re.search(r"hover|whileHover", text[max(0, m.start() - 300): m.start()], flags=re.I):
                    hits.append(Hit("HIGH", "HOVER_MOVE", f, line_of(text, m.start()),
                                    "Hover transform in JS/Motion props. Hover = colour only.", excerpt_at(text, m.start())))

    # project-level checks
    if ctx["has_motion"] and not ctx["has_reduced_motion"]:
        hits.append(Hit("HIGH", "NO_REDUCED_MOTION", "(project)", 0,
                        "Animations/transitions present but no prefers-reduced-motion rule anywhere."))
    if ctx["has_hover"] and not ctx["has_hover_guard"]:
        hits.append(Hit("LOW", "NO_HOVER_GUARD", "(project)", 0,
                        "Hover rules without @media (hover: hover): touch devices get sticky hover states."))
    if ctx["has_hover"] and not ctx["has_focus_visible"]:
        hits.append(Hit("MEDIUM", "NO_FOCUS_VISIBLE", "(project)", 0,
                        "Hover styled, :focus-visible not. Keyboard users get no ring (Tesla: inset 2px; Apple: 2px outline offset 3px)."))
    bps = ctx["breakpoints"]
    if len(bps) > 3:
        where = ", ".join(sorted(bps.keys(), key=lambda v: float(re.sub(r"[a-z]+", "", v))))
        hits.append(Hit("MEDIUM", "BREAKPOINT_SPRAWL", "(project)", 0,
                        f"{len(bps)} distinct width breakpoints ({where}). Tesla: 600/900/1200. Apple: 734/1068/1441. Pick three."))
    return hits, ctx


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=LEVELS, default=None)
    args = ap.parse_args(argv)

    hits, ctx = scan(args.paths)
    order = {lvl: i for i, lvl in enumerate(LEVELS)}
    hits.sort(key=lambda h: (order[h.severity], h.file, h.line))
    counts = {lvl: sum(1 for h in hits if h.severity == lvl) for lvl in LEVELS}

    if args.json:
        print(json.dumps({"files": ctx["files"], "counts": counts, "hits": [asdict(h) for h in hits]}, indent=1, ensure_ascii=False))
    else:
        print("## Slop scan")
        print(f"Files: {ctx['files']}  Findings: " + ", ".join(f"{counts[l]} {l}" for l in LEVELS))
        rating = next((l for l in LEVELS if counts[l]), "CLEAN")
        print(f"Overall: {rating}\n")
        for h in hits:
            loc = f"{h.file}:{h.line}" if h.line else h.file
            print(f"[{h.severity}] {h.code}  {loc}\n    {h.message}")
            if h.excerpt:
                print(f"    > {h.excerpt}")
        if not hits:
            print("No tells found. Now open it at 390 and 1440, hover a button, scroll once, screenshot.")

    if args.fail_on:
        threshold = order[args.fail_on]
        if any(order[h.severity] <= threshold for h in hits):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
