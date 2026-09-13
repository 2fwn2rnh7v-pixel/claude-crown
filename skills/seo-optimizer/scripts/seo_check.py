#!/usr/bin/env python3
"""Deterministic on-page SEO check for HTML files, directories or URLs.

Python standard library only. No install step.

Examples:
    python seo_check.py dist/
    python seo_check.py dist/index.html dist/preise/index.html
    python seo_check.py https://domain.tld/ https://domain.tld/preise --json report.json
    python seo_check.py dist/ --base-url https://domain.tld        # check self-referencing canonicals
    python seo_check.py dist/ --fail-on warning                      # stricter CI gate
    python seo_check.py https://domain.tld/ --user-agent facebookexternalhit   # HTML-limited bot view

Exit codes:
    0  no finding at or above the fail level (default: error)
    1  at least one finding at or above the fail level
    2  usage problem (no readable input)

Levels:
    error    blocks indexing or rendering -> fix before release
    warning  measurable quality loss -> schedule
    info     hint, decide deliberately

Codes (grep this block when a code is unclear):
    NOINDEX              page is noindex (info; error if also listed as indexable via --base-url expectations is out of scope)
    NOSNIPPET            nosnippet excludes page from snippets and AI features
    META_REFRESH         meta refresh redirect, use server-side 301/308 instead
    CANONICAL_MISSING    no rel=canonical
    CANONICAL_MULTIPLE   more than one canonical, Google ignores all of them
    CANONICAL_RELATIVE   canonical not absolute
    CANONICAL_ENV        canonical points to localhost/staging/preview host
    CANONICAL_NOINDEX    canonical on a noindex page (contradictory signals)
    CANONICAL_NOT_SELF   canonical differs from the page's own URL (needs --base-url or URL input)
    OG_URL_MISMATCH      og:url differs from canonical
    TITLE_MISSING / TITLE_SHORT / TITLE_LONG
    DESC_MISSING / DESC_EMPTY / DESC_SHORT / DESC_LONG
    H1_MISSING / H1_MULTIPLE / HEADING_SKIP
    LANG_MISSING         <html> without lang
    VIEWPORT_MISSING     no viewport meta, page counts as not mobile friendly
    IMG_ALT_MISSING / IMG_DIMS_MISSING
    IMG_LAZY_FIRST       first image in document is loading="lazy" (likely LCP candidate)
    THIN_CONTENT         fewer words than --min-words in rendered text
    NO_INTERNAL_LINKS    no internal <a href>, possible orphan or JS-only navigation
    OG_MISSING / OG_IMAGE_MISSING
    HREFLANG_NO_SELF     hreflang set exists but does not include the canonical URL
    HREFLANG_NO_XDEFAULT hreflang set without x-default
    JSONLD_INVALID       JSON-LD not parseable
    JSONLD_NONE          no structured data
    JSONLD_RETIRED       type no longer produces a Google rich result (FAQPage, HowTo, ...)
    JSONLD_RATING        AggregateRating/Review present, verify reviews are real and visible
    TITLE_DUPLICATE / DESC_DUPLICATE / CANONICAL_DUPLICATE   cross-page findings
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

# Thresholds with the reason next to them so they stay debatable.
TITLE_MIN = 15          # shorter titles almost never name the search goal
TITLE_MAX = 60          # above this Google usually truncates visibly
DESC_MIN = 70           # shorter snippets waste SERP space
DESC_MAX = 160          # above this it is typically cut
MIN_WORDS_DEFAULT = 150 # below this an index page is usually thin content

SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg"}

# Hosts that must never appear in a production canonical.
NON_PROD_HOSTS = (
    "localhost", "127.0.0.1", "0.0.0.0", "staging", ".local",
    "vercel.app", "netlify.app", "pages.dev", "workers.dev", "ngrok",
)

# Types Google no longer renders as a rich result (2023-2026 removals).
RETIRED_TYPES = {
    "FAQPage": "FAQ rich result removed from Search on 2026-05-07",
    "HowTo": "HowTo rich result removed 2023-09",
    "Course": "Course info rich result retired 2025 (Course list remains)",
    "ClaimReview": "Fact check rich result retired 2025",
    "Occupation": "Estimated salary rich result retired 2025",
    "LearningResource": "Learning video rich result retired 2025",
    "SpecialAnnouncement": "Special announcement retired 2025",
    "Vehicle": "Vehicle listing retired 2025",
    "Quiz": "Practice problems retired 2025",
    "WebSite": "Sitelinks search box retired 2024-11 (WebSite markup itself is harmless)",
}


class PageParser(HTMLParser):
    """Collects exactly the signals the checks below need."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.text_parts: list[str] = []
        self.skip_depth = 0
        self.current_ld: list[str] = []
        self.in_ld = False

        self.html_lang: str | None = None
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.headings: list[tuple[int, str]] = []
        self.current_heading: int | None = None
        self.heading_buf: list[str] = []
        self.images: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.jsonld_raw: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "img":
            self.images.append(a)
        elif tag == "a":
            self.anchors.append(a)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.current_heading = int(tag[1])
            self.heading_buf = []
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self.in_ld = True
            self.current_ld = []

        if tag in SKIP_TEXT_TAGS:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self.current_heading:
            self.headings.append((self.current_heading, " ".join(self.heading_buf).strip()))
            self.current_heading = None
            self.heading_buf = []
        elif tag == "script" and self.in_ld:
            self.jsonld_raw.append("".join(self.current_ld))
            self.in_ld = False
            self.current_ld = []

        if tag in SKIP_TEXT_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self.in_ld:
            self.current_ld.append(data)
        if self.current_heading:
            self.heading_buf.append(data)
        if self.skip_depth == 0:
            self.text_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())

    def meta(self, name: str) -> str | None:
        name = name.lower()
        for m in self.metas:
            if m.get("name", "").lower() == name or m.get("property", "").lower() == name:
                return m.get("content", "")
        return None

    def link_hrefs(self, rel: str) -> list[str]:
        return [l.get("href", "") for l in self.links if rel in l.get("rel", "").lower().split()]

    def hreflangs(self) -> list[dict[str, str]]:
        return [l for l in self.links
                if "alternate" in l.get("rel", "").lower().split() and l.get("hreflang")]


def load(source: str, user_agent: str) -> tuple[str, str] | None:
    """Returns (identifier, html) or None. Errors are handled here so one
    bad input does not abort the whole run."""
    if source.startswith(("http://", "https://")):
        try:
            req = Request(source, headers={"User-Agent": user_agent})
            with urlopen(req, timeout=20) as resp:  # 20 s covers slow TTFB
                charset = resp.headers.get_content_charset() or "utf-8"
                return source, resp.read().decode(charset, errors="replace")
        except Exception as exc:  # network failure must not kill the run
            print(f"[skipped] {source}: {exc}", file=sys.stderr)
            return None
    try:
        with open(source, "r", encoding="utf-8", errors="replace") as fh:
            return source, fh.read()
    except OSError as exc:
        print(f"[skipped] {source}: {exc}", file=sys.stderr)
        return None


def expand(inputs: list[str]) -> list[str]:
    out: list[str] = []
    for item in inputs:
        if item.startswith(("http://", "https://")):
            out.append(item)
        elif os.path.isdir(item):
            for root, _dirs, files in os.walk(item):
                for f in sorted(files):
                    if f.endswith((".html", ".htm")):
                        out.append(os.path.join(root, f))
        elif os.path.exists(item):
            out.append(item)
        else:
            print(f"[skipped] {item}: not found", file=sys.stderr)
    return out


def expected_url(ident: str, base_url: str | None, roots: list[str]) -> str | None:
    """Derive the URL a file should be served under, so canonical can be
    compared. Works for URL inputs directly and for files under a root dir
    when --base-url is given: dist/preise/index.html -> https://x/preise"""
    if ident.startswith(("http://", "https://")):
        return ident
    if not base_url:
        return None
    rel = None
    for r in roots:
        if os.path.isdir(r) and os.path.abspath(ident).startswith(os.path.abspath(r)):
            rel = os.path.relpath(ident, r)
            break
    if rel is None:
        return None
    rel = rel.replace(os.sep, "/")
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    elif rel.endswith(".html"):
        rel = rel[: -len(".html")]
    url = urljoin(base_url.rstrip("/") + "/", rel)
    return url


def norm(u: str) -> str:
    """Normalise for comparison: strip trailing slash except root, drop fragment."""
    p = urlparse(u)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{p.netloc.lower()}{path}"


def check_page(ident: str, html: str, exp_url: str | None, min_words: int) -> dict:
    p = PageParser()
    p.feed(html)

    findings: list[dict[str, str]] = []

    def add(level: str, code: str, msg: str) -> None:
        findings.append({"level": level, "code": code, "message": msg})

    # --- Indexability ------------------------------------------------------
    robots = (p.meta("robots") or "").lower() + " " + (p.meta("googlebot") or "").lower()
    is_noindex = "noindex" in robots
    if is_noindex:
        add("info", "NOINDEX", "Page is noindex via meta robots/googlebot.")
    if "nosnippet" in robots:
        add("warning", "NOSNIPPET", "nosnippet excludes the page from snippets and AI features.")
    if p.meta("refresh") is not None or any(
        (m.get("http-equiv", "").lower() == "refresh") for m in p.metas
    ):
        add("warning", "META_REFRESH", "Meta refresh found. Redirect server-side with 301/308.")

    canonicals = p.link_hrefs("canonical")
    canonical = canonicals[0] if canonicals else None
    if not canonicals:
        if not is_noindex:
            add("warning", "CANONICAL_MISSING", "No rel=canonical.")
    else:
        if len(canonicals) > 1:
            add("error", "CANONICAL_MULTIPLE",
                f"{len(canonicals)} canonical tags. Google ignores all of them.")
        if not canonical.startswith(("http://", "https://")):
            add("warning", "CANONICAL_RELATIVE", f"Canonical is relative: {canonical}")
        host = urlparse(canonical).netloc.lower()
        if any(x in host for x in NON_PROD_HOSTS):
            add("error", "CANONICAL_ENV", f"Canonical points to a non-production host: {canonical}")
        if is_noindex:
            add("warning", "CANONICAL_NOINDEX",
                "noindex and canonical on the same page send contradictory signals.")
        if exp_url and canonical.startswith(("http://", "https://")) \
                and norm(canonical) != norm(exp_url):
            add("warning", "CANONICAL_NOT_SELF",
                f"Canonical {canonical} differs from page URL {exp_url}.")

    og_url = p.meta("og:url")
    if og_url and canonical and og_url.startswith("http") and norm(og_url) != norm(canonical):
        add("warning", "OG_URL_MISMATCH", f"og:url {og_url} differs from canonical {canonical}.")

    # --- Title -------------------------------------------------------------
    title = p.title
    if not title:
        add("error", "TITLE_MISSING", "No <title>.")
    else:
        n = len(title)
        if n < TITLE_MIN:
            add("warning", "TITLE_SHORT", f"Title very short ({n} chars): {title!r}")
        elif n > TITLE_MAX:
            add("warning", "TITLE_LONG", f"Title {n} chars, likely truncated: {title!r}")

    # --- Description -------------------------------------------------------
    desc = p.meta("description")
    if desc is None:
        add("warning", "DESC_MISSING", "No meta description.")
    else:
        n = len(desc.strip())
        if n == 0:
            add("warning", "DESC_EMPTY", "Meta description is empty.")
        elif n < DESC_MIN:
            add("info", "DESC_SHORT", f"Description short ({n} chars).")
        elif n > DESC_MAX:
            add("info", "DESC_LONG", f"Description {n} chars, likely truncated.")

    # --- Headings ----------------------------------------------------------
    h1s = [t for lvl, t in p.headings if lvl == 1]
    if not h1s:
        add("error", "H1_MISSING", "No <h1>.")
    elif len(h1s) > 1:
        add("warning", "H1_MULTIPLE", f"{len(h1s)} <h1> elements.")
    prev = 0
    for lvl, txt in p.headings:
        if prev and lvl > prev + 1:
            add("info", "HEADING_SKIP", f"Jump from h{prev} to h{lvl}: {txt[:60]!r}")
        prev = lvl

    # --- Language / viewport -----------------------------------------------
    if not p.html_lang:
        add("warning", "LANG_MISSING", "<html> without lang attribute.")
    if p.meta("viewport") is None:
        add("error", "VIEWPORT_MISSING", "No viewport meta. Page counts as not mobile friendly.")

    # --- Images ------------------------------------------------------------
    no_alt = [i for i in p.images if "alt" not in i]
    if no_alt:
        srcs = ", ".join(i.get("src", "?")[:50] for i in no_alt[:3])
        add("warning", "IMG_ALT_MISSING", f"{len(no_alt)} image(s) without alt ({srcs}).")
    no_dims = [
        i for i in p.images
        if ("width" not in i or "height" not in i) and "aspect-ratio" not in i.get("style", "")
    ]
    if no_dims:
        add("info", "IMG_DIMS_MISSING", f"{len(no_dims)} image(s) without width/height. CLS risk.")
    if p.images and p.images[0].get("loading", "").lower() == "lazy":
        add("info", "IMG_LAZY_FIRST",
            f"First image is loading=\"lazy\" ({p.images[0].get('src', '?')[:50]}). "
            "If it is the LCP element use fetchpriority=\"high\" instead.")

    # --- Text volume -------------------------------------------------------
    words = len(p.text.split())
    if not is_noindex and words < min_words:
        add("warning", "THIN_CONTENT", f"Only {words} words in rendered text.")

    # --- Links -------------------------------------------------------------
    internal = 0
    for a in p.anchors:
        href = a.get("href", "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if not href.startswith(("http://", "https://")):
            internal += 1
        elif exp_url and urlparse(href).netloc.lower() == urlparse(exp_url).netloc.lower():
            internal += 1
    if internal == 0:
        add("warning", "NO_INTERNAL_LINKS", "No internal links. Orphan page or JS-only navigation.")

    # --- Open Graph --------------------------------------------------------
    if p.meta("og:title") is None:
        add("info", "OG_MISSING", "No Open Graph tags. Share preview is uncontrolled.")
    elif p.meta("og:image") is None:
        add("info", "OG_IMAGE_MISSING", "og:title set but no og:image (1200x630 recommended).")

    # --- hreflang ----------------------------------------------------------
    hl = p.hreflangs()
    if hl:
        langs = {l["hreflang"].lower() for l in hl}
        hrefs = {norm(l.get("href", "")) for l in hl if l.get("href", "").startswith("http")}
        if "x-default" not in langs:
            add("warning", "HREFLANG_NO_XDEFAULT", "hreflang set without x-default.")
        ref = canonical if canonical and canonical.startswith("http") else exp_url
        if ref and norm(ref) not in hrefs:
            add("warning", "HREFLANG_NO_SELF", "hreflang set does not include this page's own URL.")

    # --- Structured data ---------------------------------------------------
    types: list[str] = []
    has_rating = False

    def walk(node):
        nonlocal has_rating
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, list):
                types.extend(str(x) for x in t)
            elif t:
                types.append(str(t))
            if "aggregateRating" in node or node.get("@type") in ("Review", "AggregateRating"):
                has_rating = True
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for raw in p.jsonld_raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            add("error", "JSONLD_INVALID", f"JSON-LD not parseable: {exc}")
            continue
        walk(data)
    if not p.jsonld_raw:
        add("info", "JSONLD_NONE", "No structured data.")
    for t in sorted(set(types)):
        if t in RETIRED_TYPES:
            add("info", "JSONLD_RETIRED", f"{t}: {RETIRED_TYPES[t]}. No rich result, keep only if useful elsewhere.")
    if has_rating:
        add("info", "JSONLD_RATING", "Rating markup present. Ratings must be real, user-generated and visible on the page.")

    return {
        "source": ident,
        "url": exp_url,
        "title": title,
        "description": desc,
        "canonical": canonical,
        "h1": h1s,
        "words": words,
        "internal_links": internal,
        "schema_types": sorted(set(types)),
        "findings": findings,
    }


def cross_page_checks(pages: list[dict]) -> list[dict]:
    """Findings that only show up when comparing several pages."""
    out: list[dict] = []
    by_title: dict[str, list[str]] = defaultdict(list)
    by_desc: dict[str, list[str]] = defaultdict(list)
    by_canon: dict[str, list[str]] = defaultdict(list)
    for p in pages:
        if p["title"]:
            by_title[p["title"]].append(p["source"])
        if p["description"]:
            by_desc[p["description"]].append(p["source"])
        if p["canonical"]:
            by_canon[norm(p["canonical"]) if p["canonical"].startswith("http") else p["canonical"]].append(p["source"])
    for title, srcs in by_title.items():
        if len(srcs) > 1:
            out.append({"level": "warning", "code": "TITLE_DUPLICATE",
                        "message": f"Identical title on {len(srcs)} pages: {title!r}",
                        "sources": srcs})
    for desc, srcs in by_desc.items():
        if len(srcs) > 1:
            out.append({"level": "info", "code": "DESC_DUPLICATE",
                        "message": f"Identical description on {len(srcs)} pages.",
                        "sources": srcs})
    for canon, srcs in by_canon.items():
        if len(srcs) > 1:
            out.append({"level": "error", "code": "CANONICAL_DUPLICATE",
                        "message": f"{len(srcs)} pages canonicalise to the same URL: {canon}",
                        "sources": srcs})
    return out


ICON = {"error": "✗", "warning": "!", "info": "·"}
LEVEL_RANK = {"info": 0, "warning": 1, "error": 2}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="HTML files, directories or URLs")
    ap.add_argument("--json", metavar="PATH", help="write full report as JSON")
    ap.add_argument("--quiet", action="store_true", help="summary only")
    ap.add_argument("--base-url", metavar="URL",
                    help="production origin, e.g. https://domain.tld; enables canonical self-check for files")
    ap.add_argument("--min-words", type=int, default=MIN_WORDS_DEFAULT,
                    help=f"thin content threshold (default {MIN_WORDS_DEFAULT})")
    ap.add_argument("--fail-on", choices=["error", "warning", "info"], default="error",
                    help="exit 1 at this level or above (default error)")
    ap.add_argument("--user-agent", default="Mozilla/5.0 (compatible; seo-optimizer/1.0)",
                    help="UA for URL fetches, e.g. Googlebot or facebookexternalhit")
    args = ap.parse_args()

    targets = expand(args.inputs)
    if not targets:
        print("No readable inputs.", file=sys.stderr)
        return 2

    roots = [i for i in args.inputs if os.path.isdir(i)]
    pages: list[dict] = []
    for t in targets:
        loaded = load(t, args.user_agent)
        if loaded:
            ident, html = loaded
            pages.append(check_page(ident, html, expected_url(ident, args.base_url, roots), args.min_words))

    if not pages:
        print("No page could be read.", file=sys.stderr)
        return 2

    cross = cross_page_checks(pages)
    counts = Counter()

    for p in pages:
        for f in p["findings"]:
            counts[f["level"]] += 1
        if args.quiet:
            continue
        print(f"\n── {p['source']}" + (f"  →  {p['url']}" if p['url'] and p['url'] != p['source'] else ""))
        print(f"   Title: {p['title'][:80] or '—'}")
        print(f"   Words: {p['words']} | internal links: {p['internal_links']} "
              f"| schema: {', '.join(p['schema_types']) or '—'}")
        for f in p["findings"]:
            print(f"   {ICON[f['level']]} [{f['code']}] {f['message']}")

    for f in cross:
        counts[f["level"]] += 1
        if not args.quiet:
            print(f"\n{ICON[f['level']]} [{f['code']}] {f['message']}")
            for s in f["sources"][:5]:
                print(f"     - {s}")

    print(f"\n{'=' * 60}")
    print(f"{len(pages)} page(s) checked — "
          f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} infos")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"pages": pages, "cross_page": cross, "summary": dict(counts)},
                      fh, ensure_ascii=False, indent=2)
        print(f"JSON report: {args.json}")

    threshold = LEVEL_RANK[args.fail_on]
    failing = sum(n for lvl, n in counts.items() if LEVEL_RANK[lvl] >= threshold)
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
