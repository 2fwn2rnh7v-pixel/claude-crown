#!/usr/bin/env python3
"""sql_scan.py - static first look at the database layer of a TypeScript + Postgres/Supabase project.

Lints two things, stdlib only:
  1. SQL migrations   (default: supabase/migrations, migrations, db/migrations, sql)
       - tables created without `enable row level security`
       - RLS tables missing a policy for select / insert / update / delete
       - update policies without `with check`
       - `for all` policies, policies without a `to` clause
       - `auth.uid()` / `auth.jwt()` not wrapped in `(select ...)`
       - `security definer` functions without `set search_path`
       - foreign keys without an index
       - tables with no explicit `revoke ... from anon`
  2. TypeScript client usage (default: src, app, lib, server)
       - secret key names / literals on the client path
       - `.select('*')`, query chains without limit/range/single
       - `.from(<variable>)`, `.or(` / `.filter(` strings built with `${...}`

Every hit is a lead, not a verdict. Verify at the element before it becomes a finding.

Usage:
    python sql_scan.py <project-root> [--sql-dirs ...] [--src-dirs ...] [--json] [--fail-on HIGH]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SQL_DIRS = ["supabase/migrations", "migrations", "db/migrations", "sql", "supabase/schemas"]
SRC_DIRS = ["src", "app", "lib", "server", "pages"]
TS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".mts"}
SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "coverage", "out", ".turbo", ".output", ".supabase"}
SERVER_PATH_MARKERS = ("/api/", "/server/", "/actions/", "/functions/", "/worker", "/middleware", "route.ts",
                       ".server.", "/edge/", "/supabase/functions/", "/admin.", "/lib/supabase/server", "/scripts/")

# ---------- SQL patterns (applied to lower-cased text with comments stripped) ----------
RE_SQL_COMMENT = re.compile(r"--[^\n]*")
RE_CREATE_TABLE = re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s*\((.*?)\)\s*(?:;|with|partition|inherits|tablespace)", re.S)
RE_ENABLE_RLS = re.compile(r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s+enable\s+row\s+level\s+security")
RE_REVOKE_ANON = re.compile(r"revoke\s+[^;]*?\bon\s+(?:table\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s+from\s+[^;]*\banon\b")
RE_POLICY = re.compile(
    r"create\s+policy\s+\"?[^\"\s]+\"?\s+on\s+(?:public\.|storage\.)?\"?([a-z_][a-z0-9_]*)\"?"
    r"(?P<body>.*?);", re.S)
RE_POLICY_AS = re.compile(r"\bas\s+(permissive|restrictive)\b")
RE_POLICY_FOR = re.compile(r"\bfor\s+(select|insert|update|delete|all)\b")
RE_POLICY_TO = re.compile(r"\bto\s+[a-z_]")
RE_USING = re.compile(r"\busing\s*\(")
RE_WITH_CHECK = re.compile(r"\bwith\s+check\s*\(")
RE_AUTH_CALL = re.compile(r"\bauth\.(uid|jwt)\(\)")
RE_WRAP_BEFORE = re.compile(r"\(\s*select\s*$")


def unwrapped_auth_call(body: str) -> bool:
    """True when an auth.uid()/auth.jwt() call is not directly preceded by '(select'."""
    return any(not RE_WRAP_BEFORE.search(body[: m.start()]) for m in RE_AUTH_CALL.finditer(body))
RE_FUNC = re.compile(r"create\s+(?:or\s+replace\s+)?function\s+(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s*\((?P<sig>.*?)\)(?P<body>.*?)(?:\$\$|\$[a-z_]*\$)(?P<code>.*?)(?:\$\$|\$[a-z_]*\$)", re.S)
RE_SEC_DEFINER = re.compile(r"\bsecurity\s+definer\b")
RE_SEARCH_PATH = re.compile(r"\bset\s+search_path\b")
TYPE = r"[a-z0-9_]+(?:\s*\([0-9,\s]*\))?(?:\[\])?(?:\s+(?:with|without)\s+time\s+zone)?"
RE_FK_COL = re.compile(r"^\s*\"?([a-z_][a-z0-9_]*)\"?\s+" + TYPE + r"[^,]*?\breferences\b", re.M)
RE_FK_TABLE_LEVEL = re.compile(r"foreign\s+key\s*\(\s*\"?([a-z_][a-z0-9_]*)\"?\s*\)")
RE_CREATE_INDEX = re.compile(r"create\s+(?:unique\s+)?index\s+(?:concurrently\s+)?(?:if\s+not\s+exists\s+)?(?:\"?[a-z0-9_]+\"?\s+)?on\s+(?:only\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s*(?:using\s+[a-z]+\s*)?\(\s*\"?([a-z_][a-z0-9_]*)\"?")
RE_PK_COL = re.compile(r"^\s*\"?([a-z_][a-z0-9_]*)\"?\s+" + TYPE + r"[^,]*?\bprimary\s+key\b", re.M)
RE_PK_TABLE_LEVEL = re.compile(r"primary\s+key\s*\(\s*\"?([a-z_][a-z0-9_]*)\"?")
RE_UNIQUE_COL = re.compile(r"unique\s*\(\s*\"?([a-z_][a-z0-9_]*)\"?")
RE_GRANT_ANON = re.compile(r"grant\s+[^;]*?\bon\s+(?:table\s+)?(?:public\.)?\"?([a-z_][a-z0-9_]*)\"?\s+to\s+[^;]*\banon\b")

# ---------- TS patterns ----------
RE_USE_CLIENT = re.compile(r"""^\s*["']use client["']""", re.M)
RE_SECRET_ON_CLIENT = re.compile(r"service_role|SERVICE_ROLE|sb_secret_|SUPABASE_SECRET")
RE_PUBLIC_SECRET_NAME = re.compile(r"(NEXT_PUBLIC|VITE|EXPO_PUBLIC|REACT_APP)_[A-Z0-9_]*(SECRET|SERVICE_ROLE)")
RE_SELECT_STAR = re.compile(r"""\.select\(\s*['"`]\*['"`]\s*\)""")
RE_FROM_CALL = re.compile(r"""\.from\(\s*(?P<arg>[^)]*?)\s*\)""")
RE_LIMIT_LIKE = re.compile(r"\.(limit|range|single|maybeSingle|csv|count)\(|head:\s*true|\.insert\(|\.upsert\(|\.update\(|\.delete\(")
RE_OR_INTERP = re.compile(r"""\.(or|filter|not)\(\s*`[^`]*\$\{""")
RE_COMMENT_LINE = re.compile(r"^\s*(//|\*|/\*)")
RE_QUERY_VERB = re.compile(r"\.(select|insert|upsert|update|delete|rpc)\(")
BUILTIN_FROM = {"Array", "Buffer", "Object", "Uint8Array", "Uint16Array", "Uint32Array", "Int8Array", "Int16Array",
                "Int32Array", "Float32Array", "Float64Array", "BigInt64Array", "BigUint64Array", "Set", "Map",
                "Promise", "String", "TextEncoder"}


@dataclass
class Hit:
    area: str        # "sql" | "ts"
    check: str
    severity: str
    file: str
    line: int
    text: str


def walk(root: str, dirs: list[str], exts: set[str] | None) -> list[str]:
    bases = [os.path.join(root, d) for d in dirs if os.path.isdir(os.path.join(root, d))]
    out: list[str] = []
    for base in bases:
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                if exts is None or os.path.splitext(f)[1] in exts:
                    out.append(os.path.join(dp, f))
    return sorted(set(out))


def read(p: str) -> str:
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def is_server_path(rel: str) -> bool:
    n = "/" + rel.replace("\\", "/")
    return any(m in n for m in SERVER_PATH_MARKERS)


# ---------------- SQL ----------------
def scan_sql(root: str, files: list[str], hits: list[Hit]) -> dict:
    created: dict[str, tuple[str, int]] = {}          # table -> (file, line)
    fk_cols: dict[str, list[tuple[str, str, int]]] = {}  # table -> [(col, file, line)]
    indexed: set[tuple[str, str]] = set()             # (table, first_col)
    rls_enabled: set[str] = set()
    revoked_anon: set[str] = set()
    granted_anon: dict[str, tuple[str, int]] = {}
    policies: dict[str, set[str]] = {}                # table -> ops covered
    for path in files:
        raw = read(path)
        rel = os.path.relpath(path, root)
        text = RE_SQL_COMMENT.sub(lambda m: " " * len(m.group(0)), raw).lower()

        for m in RE_CREATE_TABLE.finditer(text):
            t, body = m.group(1), m.group(2)
            created.setdefault(t, (rel, line_of(text, m.start())))
            pk = {x.group(1) for x in RE_PK_COL.finditer(body)} | {x.group(1) for x in RE_PK_TABLE_LEVEL.finditer(body)}
            uq = {x.group(1) for x in RE_UNIQUE_COL.finditer(body)}
            for x in RE_FK_COL.finditer(body):
                col = x.group(1)
                if col not in pk and col not in uq:
                    fk_cols.setdefault(t, []).append((col, rel, line_of(text, m.start() + x.start())))
            for x in RE_FK_TABLE_LEVEL.finditer(body):
                col = x.group(1)
                if col not in pk and col not in uq:
                    fk_cols.setdefault(t, []).append((col, rel, line_of(text, m.start())))
            for x in RE_PK_TABLE_LEVEL.finditer(body):
                indexed.add((t, x.group(1)))
            for x in RE_PK_COL.finditer(body):
                indexed.add((t, x.group(1)))
            for x in RE_UNIQUE_COL.finditer(body):
                indexed.add((t, x.group(1)))
        for m in RE_ENABLE_RLS.finditer(text):
            rls_enabled.add(m.group(1))
        for m in RE_REVOKE_ANON.finditer(text):
            revoked_anon.add(m.group(1))
        for m in RE_GRANT_ANON.finditer(text):
            granted_anon.setdefault(m.group(1), (rel, line_of(text, m.start())))
        for m in RE_CREATE_INDEX.finditer(text):
            indexed.add((m.group(1), m.group(2)))

        for m in RE_POLICY.finditer(text):
            t, body = m.group(1), m.group("body")
            ln = line_of(text, m.start())
            snippet = raw.split("\n")[ln - 1].strip()[:120]
            fm = RE_POLICY_FOR.search(body)
            op = fm.group(1) if fm else "all"
            ops = {"select", "insert", "update", "delete"} if op == "all" else {op}
            policies.setdefault(t, set()).update(ops)
            if op == "all":
                hits.append(Hit("sql", "policy_for_all", "LOW", rel, ln, snippet))
            if not RE_POLICY_TO.search(body):
                hits.append(Hit("sql", "policy_without_to_clause", "LOW", rel, ln, snippet))
            if op == "update" and not RE_WITH_CHECK.search(body):
                hits.append(Hit("sql", "update_policy_without_with_check", "HIGH", rel, ln, snippet))
            if op == "insert" and not RE_WITH_CHECK.search(body):
                hits.append(Hit("sql", "insert_policy_without_with_check", "HIGH", rel, ln, snippet))
            if unwrapped_auth_call(body):
                hits.append(Hit("sql", "auth_call_not_wrapped_in_select", "MEDIUM", rel, ln, snippet))

        for m in RE_FUNC.finditer(text):
            header = m.group("body")
            code = m.group("code")
            if RE_SEC_DEFINER.search(header) and not (RE_SEARCH_PATH.search(header) or RE_SEARCH_PATH.search(code)):
                ln = line_of(text, m.start())
                hits.append(Hit("sql", "security_definer_without_search_path", "HIGH", rel, ln,
                                raw.split("\n")[ln - 1].strip()[:120]))

    for t, (rel, ln) in created.items():
        if t not in rls_enabled:
            hits.append(Hit("sql", "table_without_rls", "HIGH", rel, ln, f"create table {t}"))
        elif t not in policies:
            hits.append(Hit("sql", "rls_table_without_policies", "MEDIUM", rel, ln, f"{t}: RLS on, no policy → unusable or oversight"))
        else:
            missing = {"select", "insert", "update", "delete"} - policies[t]
            if missing:
                hits.append(Hit("sql", "rls_table_missing_ops", "LOW", rel, ln,
                                f"{t}: no policy for {', '.join(sorted(missing))} (fine only if those operations are meant to be impossible)"))
        if t not in revoked_anon:
            sev = "HIGH" if t in granted_anon else "MEDIUM"
            hits.append(Hit("sql", "anon_grant_not_revoked", sev, rel, ln,
                            f"{t}: no `revoke ... from anon` — existing Supabase projects auto-grant anon on new public tables"))
        for col, frel, fln in fk_cols.get(t, []):
            if (t, col) not in indexed:
                hits.append(Hit("sql", "fk_without_index", "MEDIUM", frel, fln, f"{t}.{col} references … but no index starts with it"))
    return {"tables": len(created), "rls_enabled": len(created and rls_enabled & set(created)),
            "sql_files": len(files)}


# ---------------- TypeScript ----------------
def scan_ts(root: str, files: list[str], hits: list[Hit]) -> dict:
    stats = {"ts_files": len(files), "queries": 0}
    for path in files:
        text = read(path)
        rel = os.path.relpath(path, root)
        lines = text.split("\n")
        client_side = bool(RE_USE_CLIENT.search(text)) or (path.endswith((".tsx", ".jsx")) and not is_server_path(rel))
        if not is_server_path(rel):
            for m in RE_SECRET_ON_CLIENT.finditer(text):
                hits.append(Hit("ts", "secret_key_outside_server_path", "CRITICAL", rel, line_of(text, m.start()),
                                lines[line_of(text, m.start()) - 1].strip()[:120]))
        for m in RE_PUBLIC_SECRET_NAME.finditer(text):
            hits.append(Hit("ts", "secret_in_public_env_name", "CRITICAL", rel, line_of(text, m.start()), m.group(0)))
        for idx, line in enumerate(lines, start=1):
            if RE_COMMENT_LINE.match(line):
                continue
            if RE_SELECT_STAR.search(line):
                hits.append(Hit("ts", "select_star", "LOW", rel, idx, line.strip()[:120]))
            fm = RE_FROM_CALL.search(line)
            if fm:
                receiver = re.search(r"([A-Za-z_$][\w$]*)$", line[: fm.start()].rstrip())
                window = "\n".join(lines[idx - 1: idx + 10])
                is_query = not (receiver and receiver.group(1) in BUILTIN_FROM) and RE_QUERY_VERB.search(window)
                if is_query:
                    stats["queries"] += 1
                    arg = fm.group("arg").strip()
                    if arg and not re.match(r"""^['"`][a-z0-9_.]+['"`]$""", arg):
                        hits.append(Hit("ts", "from_with_non_literal_table", "MEDIUM", rel, idx, line.strip()[:120]))
                    if ".select(" in window and not RE_LIMIT_LIKE.search(window):
                        hits.append(Hit("ts", "select_without_limit", "LOW", rel, idx, line.strip()[:120]))
            if RE_OR_INTERP.search(line):
                hits.append(Hit("ts", "filter_string_built_from_input", "HIGH", rel, idx, line.strip()[:120]))
    return stats


def summary(root: str, hits: list[Hit], s_sql: dict, s_ts: dict) -> str:
    def n(check: str) -> int:
        return sum(1 for h in hits if h.check == check)
    return "\n".join([
        f"Scanned: {s_sql['sql_files']} SQL files, {s_ts['ts_files']} TS files ({s_ts['queries']} .from() calls)",
        f"Tables created: {s_sql['tables']}, without RLS: {n('table_without_rls')}, RLS but no policy: {n('rls_table_without_policies')}, "
        f"missing ops: {n('rls_table_missing_ops')}, anon not revoked: {n('anon_grant_not_revoked')}",
        f"Policies: {n('update_policy_without_with_check') + n('insert_policy_without_with_check')} without with check, "
        f"{n('policy_for_all')} for all, {n('auth_call_not_wrapped_in_select')} unwrapped auth.*(), {n('policy_without_to_clause')} without to",
        f"Functions: {n('security_definer_without_search_path')} security definer without search_path; FK without index: {n('fk_without_index')}",
        f"Client: {n('secret_key_outside_server_path') + n('secret_in_public_env_name')} secret-key leads, {n('select_star')} select('*'), "
        f"{n('select_without_limit')} selects without limit, {n('from_with_non_literal_table')} dynamic table names, "
        f"{n('filter_string_built_from_input')} interpolated filter strings",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--sql-dirs", nargs="*", default=SQL_DIRS)
    ap.add_argument("--src-dirs", nargs="*", default=SRC_DIRS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=SEVERITIES)
    ap.add_argument("--max-hits", type=int, default=60)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    hits: list[Hit] = []
    s_sql = scan_sql(root, walk(root, a.sql_dirs, {".sql"}), hits)
    s_ts = scan_ts(root, walk(root, a.src_dirs, TS_EXT), hits)
    hits.sort(key=lambda h: (h.area, -SEVERITIES.index(h.severity), h.file, h.line))
    if a.json:
        print(json.dumps({"root": root, "stats": {**s_sql, **s_ts}, "hits": [asdict(h) for h in hits],
                          "summary": summary(root, hits, s_sql, s_ts)}, indent=2))
    else:
        print(f"sql_scan: {root}")
        for area in ("sql", "ts"):
            ah = [h for h in hits if h.area == area]
            print(f"\n== {area.upper()}: {len(ah)} hits")
            for h in ah[: a.max_hits]:
                print(f"  [{h.severity}] {h.check}  {h.file}:{h.line}  {h.text}")
            if len(ah) > a.max_hits:
                print(f"  ... {len(ah) - a.max_hits} more (--max-hits / --json)")
        print("\n" + summary(root, hits, s_sql, s_ts))
    if a.fail_on and any(SEVERITIES.index(h.severity) >= SEVERITIES.index(a.fail_on) for h in hits):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
