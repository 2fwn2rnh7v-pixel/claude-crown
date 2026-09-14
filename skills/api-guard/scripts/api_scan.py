#!/usr/bin/env python3
"""api_scan.py - static first look at API usage in a TypeScript/JavaScript project.

Implements the ripgrep patterns from references/quick-scan.md in pure Python (stdlib only).
Every hit is a lead, not a verdict: verify at the element before it becomes a finding.

Usage:
    python api_scan.py <project-root> [--dirs app src ...] [--json] [--fail-on HIGH] [--max-hits 40]

Levels (see SKILL.md):
    1  secrets in the client path            -> CRITICAL leads
    2  handlers without limit / auth          -> HIGH / MEDIUM leads
    3  abuse and cost risks                   -> MEDIUM leads
    4  efficiency (N+1, debounce, caching)    -> LOW leads

Exit code 0; with --fail-on LEVEL exit 1 when any hit is at least that severe.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts", ".cjs"}
SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "coverage", "out", ".turbo",
             ".output", ".wrangler", ".vercel", "__pycache__", ".cache"}
DEFAULT_DIRS = ["app", "src", "server", "lib", "routes", "functions", "pages", "api"]
SERVER_PATH_MARKERS = ("/api/", "/server/", "/actions/", "/functions/", "/worker", "/middleware",
                       "route.ts", "route.js", ".server.", "/edge/", "/supabase/functions/")

# ---------- Level 1 ----------
RE_PUBLIC_ENV_SECRET = re.compile(
    r"(NEXT_PUBLIC|VITE|REACT_APP|EXPO_PUBLIC)_[A-Z0-9_]*(KEY|SECRET|TOKEN|PASSWORD|SERVICE_ROLE)")
# keys a provider designed to be public: still a lead (RLS / referrer restriction / budget alert), not CRITICAL
RE_DESIGNED_PUBLIC = re.compile(r"ANON|PUBLISHABLE|PUBLIC_KEY|_PK\b|MAPS|ANALYTICS|POSTHOG|SENTRY|RECAPTCHA|TURNSTILE|SITE_KEY")
RE_BROWSER_SDK = re.compile(r"dangerouslyAllowBrowser")
RE_KEY_LITERAL = re.compile(r"""['"`](sk-[A-Za-z0-9_-]{8,}|sk_live_|rk_live_|sb_secret_|xoxb-|ghp_[A-Za-z0-9]{8,}|AIza[0-9A-Za-z_-]{10,})""")
RE_USE_CLIENT = re.compile(r"""^\s*["']use client["']""", re.MULTILINE)
RE_EXTERNAL_FETCH = re.compile(r"""fetch\(\s*['"`]https?://""")
RE_SECRET_KEY_NAME = re.compile(r"service_role|SERVICE_ROLE|sb_secret_")

# ---------- Level 2 ----------
RE_HANDLER = re.compile(
    r"""export\s+(async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\b"""
    r"""|export\s+const\s+(GET|POST|PUT|PATCH|DELETE)\s*="""
    r"""|^\s*["']use server["']"""
    r"""|createServerFn\(""", re.MULTILINE)
LIMIT_PATTERN = r"ratelimit|rateLimit|checkLimit|Ratelimit|throttle|\.limit\(|bucket|quota"
AUTH_PATTERN = (r"\brequire[A-Z]\w*\(|getUser|getSession|\bauth\(|getServerSession|getClaims|verifyToken"
                r"|currentUser|withAuth|authorize\(|assertUser|assertSession")
RE_PAID_SDK = re.compile(r"""new\s+(Anthropic|OpenAI|Stripe|Replicate|Mistral|GoogleGenerativeAI)\s*\(|from\s+['"](@anthropic-ai/sdk|openai|stripe|replicate|@google/generative-ai|@mistralai/mistralai)['"]""")

# ---------- Level 3 ----------
RE_COMMENT_LINE = re.compile(r"^\s*(//|\*|/\*)")
RE_FETCH_DEF = re.compile(r"^\s*(export\s+)?(async\s+)?fetch\s*\(")        # Worker/handler method definition
RE_FETCH_CALL = re.compile(r"(?<![.\w])fetch\(\s*(?!\))")                  # a call with an argument, not .fetch(
RE_TIMEOUT = re.compile(r"signal|AbortSignal|timeout")
RE_POLLING = re.compile(r"setInterval\(")
RE_RETRY = re.compile(r"\b(maxRetries|retries|retryCount)\b|\bretry\s*\(|\.retry\(")
RE_BACKOFF = re.compile(r"backoff|jitter|Retry-After|exponential", re.IGNORECASE)
RE_CLIENT_PARAMS = re.compile(r"\b(model|maxTokens|max_tokens|quality|resolution)\s*[:=]\s*(body|req|params|searchParams|input|data)\b")

# ---------- Level 4 ----------
RE_FOR_LOOP = re.compile(r"\bfor\s*\(.*\)\s*\{")
RE_AWAIT = re.compile(r"\bawait\b")
RE_MAP_ASYNC = re.compile(r"\.map\(\s*async")
RE_ONCHANGE = re.compile(r"onChange")
RE_SEARCH_INPUT = re.compile(r"<input|<Input|type=\"search\"|search|suche|autocomplete|typeahead|suggest", re.IGNORECASE)
RE_REMOTE_CALL = re.compile(r"(?<![.\w])fetch\(|useQuery|useSWR|useServerFn|useAction|startTransition|createServerFn")
RE_DEBOUNCE = re.compile(r"debounce|useDeferredValue|throttle", re.IGNORECASE)
RE_CACHING = re.compile(r"revalidate|Cache-Control|stale-while-revalidate|unstable_cache|cacheTag|cacheLife|use cache")


@dataclass
class Hit:
    level: int
    check: str
    severity: str
    file: str
    line: int
    text: str


def iter_files(root: str, dirs: list[str]) -> list[str]:
    bases = [os.path.join(root, d) for d in dirs if os.path.isdir(os.path.join(root, d))]
    if not bases:
        bases = [root]
    seen: set[str] = set()
    out: list[str] = []
    for base in bases:
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1] in EXTENSIONS:
                    p = os.path.join(dirpath, fn)
                    if p not in seen:
                        seen.add(p)
                        out.append(p)
    return sorted(out)


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def snippet(lines: list[str], lineno: int) -> str:
    return lines[lineno - 1].strip()[:140] if 0 < lineno <= len(lines) else ""


def is_server_path(rel: str) -> bool:
    norm = "/" + rel.replace("\\", "/")
    return any(m in norm for m in SERVER_PATH_MARKERS)


def effect_without_deps(text: str) -> list[int]:
    """Line numbers of useEffect( calls whose argument list has no dependency array."""
    hits: list[int] = []
    for m in re.finditer(r"useEffect\s*\(", text):
        i = m.end()
        depth = 1
        start = i
        in_str: str | None = None
        while i < len(text) and depth > 0:
            c = text[i]
            if in_str:
                if c == "\\":
                    i += 1
                elif c == in_str:
                    in_str = None
            elif c in "'\"`":
                in_str = c
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            i += 1
        args = text[start:i - 1]
        # find end of the callback body: first '{' ... matching '}'
        brace = args.find("{")
        if brace == -1:
            continue
        d = 0
        j = brace
        while j < len(args):
            if args[j] == "{":
                d += 1
            elif args[j] == "}":
                d -= 1
                if d == 0:
                    break
            j += 1
        remainder = args[j + 1:]
        if not ("," in remainder and "[" in remainder):
            hits.append(line_of(text, m.start()))
    return hits


def scan(root: str, dirs: list[str], auth_extra: str = "", limit_extra: str = "") -> tuple[list[Hit], dict]:
    hits: list[Hit] = []
    files = iter_files(root, dirs)
    stats = {"files": len(files), "handlers": 0, "handlers_no_limit": 0,
             "handlers_no_limit_paid": 0, "handlers_no_auth": 0, "caching_present": False}
    re_limit = re.compile(LIMIT_PATTERN + (f"|{limit_extra}" if limit_extra else ""), re.IGNORECASE)
    re_auth = re.compile(AUTH_PATTERN + (f"|{auth_extra}" if auth_extra else ""))

    for path in files:
        text = read(path)
        rel = os.path.relpath(path, root)
        lines = text.split("\n")
        is_client = bool(RE_USE_CLIENT.search(text)) or path.endswith((".tsx", ".jsx"))
        server_path = is_server_path(rel)

        def add(level: int, check: str, sev: str, lineno: int) -> None:
            hits.append(Hit(level, check, sev, rel, lineno, snippet(lines, lineno)))

        # Level 1
        for m in RE_PUBLIC_ENV_SECRET.finditer(text):
            if RE_DESIGNED_PUBLIC.search(m.group(0)):
                add(1, "public_key_verify_restrictions", "LOW", line_of(text, m.start()))
            else:
                add(1, "public_env_secret", "CRITICAL", line_of(text, m.start()))
        for m in RE_BROWSER_SDK.finditer(text):
            add(1, "browser_sdk", "CRITICAL", line_of(text, m.start()))
        for m in RE_KEY_LITERAL.finditer(text):
            add(1, "key_literal", "CRITICAL", line_of(text, m.start()))
        if RE_USE_CLIENT.search(text):
            for m in RE_EXTERNAL_FETCH.finditer(text):
                add(1, "client_direct_external_fetch", "CRITICAL", line_of(text, m.start()))
        if not server_path:
            for m in RE_SECRET_KEY_NAME.finditer(text):
                add(1, "secret_key_outside_server_path", "CRITICAL", line_of(text, m.start()))

        # Level 2
        hm = RE_HANDLER.search(text)
        if hm:
            stats["handlers"] += 1
            paid = bool(RE_EXTERNAL_FETCH.search(text) or RE_PAID_SDK.search(text))
            has_limit = bool(re_limit.search(text))
            has_auth = bool(re_auth.search(text))
            ln = line_of(text, hm.start())
            if not has_limit:
                stats["handlers_no_limit"] += 1
                if paid:
                    stats["handlers_no_limit_paid"] += 1
                    add(2, "handler_no_limit_paid_upstream", "HIGH", ln)
                else:
                    add(2, "handler_no_limit", "MEDIUM", ln)
            if not has_auth:
                stats["handlers_no_auth"] += 1
                add(2, "handler_no_auth", "CRITICAL" if paid else "MEDIUM", ln)

        # Level 3 — line-aware: comments and method definitions are not calls
        retry_line = 0
        for idx, line in enumerate(lines, start=1):
            if RE_COMMENT_LINE.match(line):
                continue
            if RE_FETCH_CALL.search(line) and not RE_FETCH_DEF.match(line):
                window = "\n".join(lines[idx - 1: idx + 6])
                if not RE_TIMEOUT.search(window):
                    add(3, "fetch_without_timeout", "MEDIUM", idx)
            if not retry_line and RE_RETRY.search(line):
                retry_line = idx
        for m in RE_POLLING.finditer(text):
            add(3, "polling_setInterval", "MEDIUM", line_of(text, m.start()))
        for ln in effect_without_deps(text):
            add(3, "useEffect_without_deps", "MEDIUM", ln)
        if retry_line and not RE_BACKOFF.search(text):
            add(3, "retry_without_backoff", "MEDIUM", retry_line)
        for m in RE_CLIENT_PARAMS.finditer(text):
            add(3, "client_controls_expensive_params", "HIGH", line_of(text, m.start()))

        # Level 4
        for m in RE_FOR_LOOP.finditer(text):
            ln = line_of(text, m.start())
            window = "\n".join(lines[ln: ln + 6])
            if RE_AWAIT.search(window):
                add(4, "await_in_loop_n_plus_1", "LOW", ln)
        for m in RE_MAP_ASYNC.finditer(text):
            add(4, "map_async_fanout", "LOW", line_of(text, m.start()))
        # a search-like text input that triggers a remote call on change, with no debounce in the file
        if is_client and RE_REMOTE_CALL.search(text) and not RE_DEBOUNCE.search(text):
            for idx, line in enumerate(lines, start=1):
                if RE_ONCHANGE.search(line):
                    around = "\n".join(lines[max(0, idx - 3): idx + 2])
                    if RE_SEARCH_INPUT.search(around):
                        add(4, "onChange_without_debounce", "LOW", idx)
                        break
        if RE_CACHING.search(text):
            stats["caching_present"] = True

    return hits, stats


def summary_block(root: str, dirs: list[str], hits: list[Hit], stats: dict) -> str:
    def n(check: str) -> int:
        return sum(1 for h in hits if h.check == check)
    l1_crit = sum(1 for h in hits if h.level == 1 and h.severity == "CRITICAL")
    l1_pub = n("public_key_verify_restrictions")
    scanned = ", ".join(d for d in dirs if os.path.isdir(os.path.join(root, d))) or root
    return "\n".join([
        f"Scanned: {scanned} ({stats['files']} files)",
        f"Level 1: {l1_crit} critical hits, {l1_pub} designed-public keys to verify "
        f"(bundle check pending - run the post-build grep from quick-scan.md)",
        f"Level 2: {stats['handlers']} handlers total, {stats['handlers_no_limit']} without limit, "
        f"{stats['handlers_no_limit_paid']} of those with a paid upstream call, {stats['handlers_no_auth']} without auth check",
        f"Level 3: {n('polling_setInterval')} polling sites, {n('fetch_without_timeout')} fetches without timeout, "
        f"{n('retry_without_backoff')} retry sites without backoff, {n('useEffect_without_deps')} effects without deps",
        f"Level 4: {n('await_in_loop_n_plus_1') + n('map_async_fanout')} N+1 suspects, "
        f"{n('onChange_without_debounce')} search fields without debounce, caching: "
        f"{'present' if stats['caching_present'] else 'absent'}",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--dirs", nargs="*", default=DEFAULT_DIRS, help="subdirectories to scan (default: common ones; falls back to root)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--fail-on", choices=SEVERITIES, help="exit 1 if any hit is at least this severe")
    ap.add_argument("--max-hits", type=int, default=60, help="hits to print per level in text mode")
    ap.add_argument("--auth-pattern", default="", help="extra regex for the project's auth helper (e.g. 'withTenant\\(')")
    ap.add_argument("--limit-pattern", default="", help="extra regex for the project's limiter (e.g. 'guardQuota\\(')")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    hits, stats = scan(root, args.dirs, args.auth_pattern, args.limit_pattern)
    hits.sort(key=lambda h: (h.level, -SEVERITIES.index(h.severity), h.file, h.line))

    if args.json:
        print(json.dumps({"root": root, "stats": stats, "hits": [asdict(h) for h in hits],
                          "summary": summary_block(root, args.dirs, hits, stats)}, indent=2))
    else:
        print(f"api_scan: {root}")
        for level in (1, 2, 3, 4):
            lh = [h for h in hits if h.level == level]
            print(f"\n== Level {level}: {len(lh)} hits")
            for h in lh[: args.max_hits]:
                print(f"  [{h.severity}] {h.check}  {h.file}:{h.line}  {h.text}")
            if len(lh) > args.max_hits:
                print(f"  ... {len(lh) - args.max_hits} more (raise --max-hits or use --json)")
        print("\n" + summary_block(root, args.dirs, hits, stats))

    if args.fail_on:
        threshold = SEVERITIES.index(args.fail_on)
        if any(SEVERITIES.index(h.severity) >= threshold for h in hits):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
