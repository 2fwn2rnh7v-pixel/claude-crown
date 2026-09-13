#!/usr/bin/env python3
"""Crawl and index control check for a live site: robots.txt, sitemap, status codes,
redirects, noindex, canonical consistency, soft-404 behaviour, HTML-limited bot view.

Python standard library only.

Examples:
    python crawl_check.py https://domain.tld
    python crawl_check.py https://domain.tld --sitemap https://domain.tld/sitemap-pages.xml --limit 300
    python crawl_check.py https://domain.tld --json crawl.json
    python crawl_check.py https://domain.tld --skip-404      # site intentionally has no 404 route

Exit codes:
    0  no error-level finding
    1  at least one error
    2  usage problem (origin unreachable)

Codes:
    ROBOTS_MISSING        robots.txt not 200 (Google treats 5xx as "do not crawl" for a while)
    ROBOTS_BLOCKS_ALL     Disallow: / for * or Googlebot
    ROBOTS_BLOCKS_ASSETS  CSS/JS paths disallowed, Google cannot render the page
    ROBOTS_NO_SITEMAP     no Sitemap: line
    ROBOTS_AI_TRAINING    AI training bots not addressed (info, deliberate decision)
    SITEMAP_MISSING       sitemap not reachable / not XML
    SITEMAP_EMPTY         zero <loc> entries
    SITEMAP_FOREIGN_HOST  sitemap URL on another host
    SITEMAP_LASTMOD_ALL_SAME  every lastmod identical (signal devalued)
    URL_STATUS            sitemap URL does not answer 200 (after redirects: URL_REDIRECT)
    URL_REDIRECT          sitemap URL redirects, sitemap should list the final URL
    URL_NOINDEX           sitemap URL is noindex (meta or X-Robots-Tag)
    URL_BLOCKED           sitemap URL disallowed by robots.txt
    URL_CANONICAL_OTHER   sitemap URL canonicalises to a different URL
    URL_NO_HTML           sitemap URL is not text/html
    SOFT_404              random non-existent path answers 200
    HOME_REDIRECT_CHAIN   origin takes more than one hop to settle (http->https->www)
    BOT_VIEW_DIFFERS      title differs between browser UA and HTML-limited bot UA
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import string
import sys
import urllib.robotparser as robotparser
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
import urllib.request as ur
from urllib.request import Request
import xml.etree.ElementTree as ET

UA_BROWSER = "Mozilla/5.0 (compatible; seo-optimizer-crawl/1.0)"
UA_HTML_LIMITED = "facebookexternalhit/1.1"
AI_TRAINING_BOTS = ("GPTBot", "ClaudeBot", "CCBot", "Google-Extended", "Applebot-Extended",
                    "Bytespider", "meta-externalagent")
ASSET_HINTS = ("/_next/", "/assets/", "/static/", "/_astro/", ".css", ".js")


class NoRedirect(ur.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.robots = ""
        self.canonical = None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name", "").lower() in ("robots", "googlebot"):
            self.robots += " " + a.get("content", "").lower()
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split() and self.canonical is None:
            self.canonical = a.get("href", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def fetch(url: str, ua: str = UA_BROWSER, follow: bool = True, timeout: int = 20):
    """Returns dict(status, final_url, headers, body|None). Never raises."""
    opener = ur.build_opener() if follow else ur.build_opener(NoRedirect)
    req = Request(url, headers={"User-Agent": ua, "Accept-Encoding": "gzip"})
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            charset = resp.headers.get_content_charset() or "utf-8"
            return {"status": resp.status, "final_url": resp.geturl(),
                    "headers": dict(resp.headers), "body": raw.decode(charset, errors="replace")}
    except HTTPError as e:
        return {"status": e.code, "final_url": e.geturl(), "headers": dict(e.headers), "body": None,
                "location": e.headers.get("Location")}
    except URLError as e:
        return {"status": 0, "final_url": url, "headers": {}, "body": None, "error": str(e.reason)}
    except Exception as e:  # timeouts, decode errors
        return {"status": 0, "final_url": url, "headers": {}, "body": None, "error": str(e)}


def norm(u: str) -> str:
    p = urlparse(u)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{p.netloc.lower()}{path}"


def parse_sitemap(xml_text: str) -> tuple[list[str], list[dict]]:
    """Returns (child_sitemaps, url_entries[{loc,lastmod}])."""
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return [], []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        return [s.text.strip() for s in root.findall(".//sm:sitemap/sm:loc", ns) if s.text], []
    entries = []
    for u in root.findall(".//sm:url", ns):
        loc = u.find("sm:loc", ns)
        lm = u.find("sm:lastmod", ns)
        if loc is not None and loc.text:
            entries.append({"loc": loc.text.strip(), "lastmod": lm.text.strip() if lm is not None and lm.text else None})
    return [], entries


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("origin", help="https://domain.tld")
    ap.add_argument("--sitemap", help="explicit sitemap URL (default: from robots.txt, else /sitemap.xml)")
    ap.add_argument("--limit", type=int, default=200, help="max sitemap URLs to fetch (default 200)")
    ap.add_argument("--json", metavar="PATH")
    ap.add_argument("--skip-404", action="store_true", help="skip soft-404 probe")
    ap.add_argument("--skip-bot-view", action="store_true", help="skip HTML-limited bot comparison")
    args = ap.parse_args()

    origin = args.origin.rstrip("/")
    if not origin.startswith("http"):
        origin = "https://" + origin
    host = urlparse(origin).netloc.lower()
    findings: list[dict] = []

    def add(level, code, msg, url=None):
        findings.append({"level": level, "code": code, "message": msg, "url": url})

    # --- origin & redirect chain --------------------------------------------
    hops = 0
    cur = origin + "/"
    seen = []
    while hops < 6:
        r = fetch(cur, follow=False)
        seen.append((cur, r["status"]))
        if r["status"] in (301, 302, 307, 308) and r.get("location"):
            cur = urljoin(cur, r["location"])
            hops += 1
            continue
        break
    if seen[-1][1] == 0:
        print(f"Origin unreachable: {seen}", file=sys.stderr)
        return 2
    if hops > 1:
        add("warning", "HOME_REDIRECT_CHAIN", f"{hops} hops: " + " → ".join(f"{u} ({s})" for u, s in seen))
    final_origin = seen[-1][0].rstrip("/")
    print(f"Origin: {origin}  →  {final_origin}  ({seen[-1][1]})")

    # --- robots.txt ---------------------------------------------------------
    robots_url = final_origin + "/robots.txt"
    rr = fetch(robots_url)
    rp = robotparser.RobotFileParser()
    sitemaps_from_robots: list[str] = []
    if rr["status"] != 200 or rr["body"] is None:
        add("error" if rr["status"] >= 500 else "warning", "ROBOTS_MISSING",
            f"robots.txt answered {rr['status']}. 5xx makes Google pause crawling; 404 means everything allowed.")
        rp.parse([])
    else:
        lines = rr["body"].splitlines()
        rp.parse(lines)
        for ln in lines:
            if ln.lower().startswith("sitemap:"):
                sitemaps_from_robots.append(ln.split(":", 1)[1].strip())
        if not sitemaps_from_robots:
            add("warning", "ROBOTS_NO_SITEMAP", "No Sitemap: line in robots.txt.")
        for agent in ("*", "Googlebot"):
            if not rp.can_fetch(agent, final_origin + "/"):
                add("error", "ROBOTS_BLOCKS_ALL", f"robots.txt disallows / for {agent}.")
        # crude probe: /_next/app.js, /assets/app.js, ... and /app.css style
        for h in ASSET_HINTS:
            probe = final_origin + (h + "app.js" if h.endswith("/") else "/app" + h)
            if not rp.can_fetch("Googlebot", probe):
                add("error", "ROBOTS_BLOCKS_ASSETS", f"robots.txt blocks asset path pattern {probe}. Google cannot render.")
                break
        body_l = rr["body"].lower()
        addressed = [b for b in AI_TRAINING_BOTS if b.lower() in body_l]
        if not addressed:
            add("info", "ROBOTS_AI_TRAINING",
                "No AI training bots addressed (GPTBot, ClaudeBot, CCBot, Google-Extended). Decide deliberately; "
                "does not affect Google Search.")
    print(f"robots.txt: {rr['status']}  sitemaps declared: {len(sitemaps_from_robots)}")

    # --- sitemap ------------------------------------------------------------
    candidates = [args.sitemap] if args.sitemap else (sitemaps_from_robots or [final_origin + "/sitemap.xml"])
    entries: list[dict] = []
    queue = list(candidates)
    visited = set()
    while queue and len(entries) < args.limit * 5:
        sm = queue.pop(0)
        if sm in visited:
            continue
        visited.add(sm)
        r = fetch(sm)
        if r["status"] != 200 or r["body"] is None:
            add("error", "SITEMAP_MISSING", f"{sm} answered {r['status']}.", sm)
            continue
        body = r["body"]
        if sm.endswith(".gz") and not body.lstrip().startswith("<"):
            add("warning", "SITEMAP_MISSING", f"{sm}: gz payload not decoded, check manually.", sm)
            continue
        children, urls = parse_sitemap(body)
        if not children and not urls:
            add("error", "SITEMAP_EMPTY", f"{sm}: no <loc> entries or not valid XML.", sm)
        queue.extend(children)
        entries.extend(urls)
    print(f"sitemap(s): {len(visited)} file(s), {len(entries)} URL(s)")

    if entries:
        lastmods = [e["lastmod"] for e in entries if e["lastmod"]]
        if len(lastmods) >= 5 and len(set(lastmods)) == 1:
            add("warning", "SITEMAP_LASTMOD_ALL_SAME",
                f"All {len(lastmods)} lastmod values identical ({lastmods[0]}). Google ignores devalued lastmod.")
        foreign = [e["loc"] for e in entries if urlparse(e["loc"]).netloc.lower() != host and urlparse(e["loc"]).netloc.lower() != urlparse(final_origin).netloc.lower()]
        if foreign:
            add("error", "SITEMAP_FOREIGN_HOST", f"{len(foreign)} URL(s) on another host, e.g. {foreign[0]}", foreign[0])

    # --- per-URL checks -----------------------------------------------------
    checked = 0
    url_rows: list[dict] = []
    for e in entries[: args.limit]:
        u = e["loc"]
        row = {"url": u}
        if not rp.can_fetch("Googlebot", u):
            add("error", "URL_BLOCKED", "Sitemap URL disallowed by robots.txt.", u)
        r0 = fetch(u, follow=False)
        row["status"] = r0["status"]
        if r0["status"] in (301, 302, 307, 308):
            add("warning", "URL_REDIRECT", f"{r0['status']} → {r0.get('location')}. List the final URL instead.", u)
            r = fetch(u)
        else:
            r = r0
        if r["status"] != 200:
            add("error", "URL_STATUS", f"Answers {r['status']}.", u)
            url_rows.append(row)
            checked += 1
            continue
        ctype = r["headers"].get("Content-Type", "")
        if "html" not in ctype.lower():
            add("warning", "URL_NO_HTML", f"Content-Type {ctype}.", u)
        xrobots = r["headers"].get("X-Robots-Tag", "").lower()
        hp = HeadParser()
        hp.feed(r["body"] or "")
        row["title"] = hp.title.strip()
        row["canonical"] = hp.canonical
        if "noindex" in hp.robots or "noindex" in xrobots:
            add("error", "URL_NOINDEX", "noindex on a sitemap URL. Remove one of the two.", u)
        if hp.canonical and hp.canonical.startswith("http") and norm(hp.canonical) != norm(r["final_url"]):
            add("warning", "URL_CANONICAL_OTHER", f"canonical → {hp.canonical}. Sitemap should list canonicals only.", u)
        url_rows.append(row)
        checked += 1
    print(f"URLs fetched: {checked}")

    # --- soft-404 probe -----------------------------------------------------
    if not args.skip_404:
        rnd = "".join(random.choices(string.ascii_lowercase, k=12))
        probe = f"{final_origin}/seo-optimizer-probe-{rnd}"
        r = fetch(probe)
        if r["status"] == 200:
            add("error", "SOFT_404", f"{probe} answers 200. Non-existent paths must return 404/410 (SPA fallback?).", probe)
        print(f"soft-404 probe: {r['status']}")

    # --- HTML-limited bot view ----------------------------------------------
    if not args.skip_bot_view:
        a = fetch(final_origin + "/", ua=UA_BROWSER)
        b = fetch(final_origin + "/", ua=UA_HTML_LIMITED)
        ta, tb = HeadParser(), HeadParser()
        ta.feed(a["body"] or "")
        tb.feed(b["body"] or "")
        if a["status"] == 200 and b["status"] == 200 and ta.title.strip() != tb.title.strip():
            add("warning", "BOT_VIEW_DIFFERS",
                f"Title differs by UA: browser={ta.title.strip()!r} bot={tb.title.strip()!r}. "
                "Streaming metadata or cloaking?")
        elif b["status"] in (403, 429, 503) and a["status"] == 200:
            add("error", "BOT_VIEW_DIFFERS",
                f"Bot UA gets {b['status']}, browser gets 200. CDN/WAF bot protection blocks crawlers.")
        print(f"bot view: browser {a['status']} / html-limited bot {b['status']}")

    # --- output -------------------------------------------------------------
    counts = {"error": 0, "warning": 0, "info": 0}
    icon = {"error": "✗", "warning": "!", "info": "·"}
    print()
    for f in findings:
        counts[f["level"]] += 1
        loc = f"  ({f['url']})" if f["url"] else ""
        print(f"{icon[f['level']]} [{f['code']}] {f['message']}{loc}")
    print(f"\n{'=' * 60}\n{counts['error']} errors, {counts['warning']} warnings, {counts['info']} infos")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"origin": origin, "final_origin": final_origin, "robots_status": rr["status"],
                       "sitemaps": sorted(visited), "urls": url_rows, "findings": findings,
                       "summary": counts}, fh, ensure_ascii=False, indent=2)
        print(f"JSON report: {args.json}")

    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
