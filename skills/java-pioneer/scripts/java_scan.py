#!/usr/bin/env python3
"""java_scan.py - static first look at a Spring Boot project against the java-pioneer non-negotiables.

Stdlib only. Reads Java sources, application*.yml|yaml|properties, pom.xml / build.gradle(.kts).
Every hit is a lead, not a verdict: verify at the element before it becomes a finding.

Checks (severity):
  build   spring boot line and its OSS support state (INFO/HIGH), java release (INFO)
  config  open-in-view not false (MEDIUM), ddl-auto update/create outside local (HIGH),
          stack traces / messages in error responses (LOW), actuator exposure (HIGH),
          literal secrets (HIGH), h2 console (MEDIUM), swagger-ui enabled (LOW)
  java    string-built JPQL/SQL (CRITICAL), entity returned from a controller (HIGH),
          csrf disabled with cookie auth (HIGH) / with stateless JWT (LOW),
          permitAll on everything (HIGH), CORS credentials + wildcard (HIGH),
          @RequestBody without @Valid (MEDIUM), field @Autowired (MEDIUM), @Data on @Entity (HIGH),
          swallowed exception (MEDIUM), Sort.by(<variable>) (MEDIUM), java.util.Random for
          tokens (HIGH), Optional field/parameter (LOW), System.out / printStackTrace (LOW),
          ToOne association without LAZY (LOW), long id in a response record (LOW)

Usage:
    python java_scan.py <project-root> [--json] [--fail-on HIGH] [--max-hits 60]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

SEVERITIES = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
SKIP_DIRS = {"target", "build", ".git", ".gradle", ".idea", "node_modules", "out", ".mvn"}
LOCAL_PROFILE = re.compile(r"application-(local|dev|development|test|it)\.")

# Spring Boot lines and OSS support end (verified 2026-09-15 against endoflife.date/spring-boot)
BOOT_OSS_END = {"4.1": "2027-07-31", "4.0": "2026-12-31", "3.5": "2026-06-30", "3.4": "2025-12-31",
                "3.3": "2025-06-30", "3.2": "2024-12-31", "3.1": "2024-06-30", "3.0": "2023-12-31", "2.7": "2023-06-30"}
TODAY = "2026-09-15"

# ---------- Java ----------
RE_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
RE_STRING_CONCAT_QUERY = re.compile(r"(createQuery|createNativeQuery|@Query|@NativeQuery|\.sql|jdbcTemplate\.(query|update|execute)|jdbcClient\.sql)\s*\(?[^;]*?\"[^\"]*\"\s*\+\s*[A-Za-z_]", re.S)
RE_ENTITY_CLASS = re.compile(r"@Entity\b[^;]*?\bclass\s+([A-Z]\w*)", re.S)
RE_REST_CONTROLLER = re.compile(r"@RestController\b")
RE_CSRF_DISABLE = re.compile(r"csrf\s*\(\s*(AbstractHttpConfigurer::disable|\w+\s*->\s*\w+\.disable\(\))\s*\)|\.csrf\(\)\.disable\(\)")
RE_STATELESS = re.compile(r"SessionCreationPolicy\.STATELESS|oauth2ResourceServer")
RE_PERMIT_ALL_EVERYTHING = re.compile(r"(anyRequest\(\)|requestMatchers\(\s*\"/\*\*\"\s*\))\s*\.permitAll\(\)")
RE_CORS_CREDENTIALS = re.compile(r"setAllowCredentials\(\s*true\s*\)|allowCredentials\(\s*true\s*\)|allowCredentials\s*=\s*\"true\"")
RE_CORS_WILDCARD = re.compile(r"(setAllowedOrigins|allowedOrigins|setAllowedOriginPatterns|allowedOriginPatterns)\s*\(\s*(List\.of\(\s*)?\"\*\"|origins\s*=\s*\"\*\"")
RE_REQUEST_BODY = re.compile(r"@RequestBody\b")
RE_VALID = re.compile(r"@Valid(ated)?\b")
RE_FIELD_AUTOWIRED = re.compile(r"@Autowired\s*\n?\s*(private|protected|public)?\s*(final\s+)?[A-Z][\w<>,?\s]*\s+\w+\s*;")
RE_DATA_ON_ENTITY = re.compile(r"(@Data\b[^;]*?@Entity\b|@Entity\b[^;]*?@Data\b)", re.S)
RE_SWALLOWED = re.compile(r"catch\s*\(\s*[\w.]+\s+\w+\s*\)\s*\{\s*(\w+\.printStackTrace\(\);\s*)?\}")
RE_SORT_BY_VAR = re.compile(r"Sort\.by\(\s*(?:Sort\.Direction\.\w+\s*,\s*)?([a-z]\w*)\s*\)")
RE_RANDOM = re.compile(r"new\s+Random\s*\(|Math\.random\s*\(")
RE_SECURITY_CONTEXT_FILE = re.compile(r"token|password|secret|otp|reset|nonce|session", re.I)
RE_OPTIONAL_FIELD_PARAM = re.compile(r"(private|protected)\s+(final\s+)?Optional<|\(\s*[^)]*\bOptional<[^>]+>\s+\w+\s*[,)]")
RE_SYSOUT = re.compile(r"System\.(out|err)\.print|\.printStackTrace\(\)")
RE_TOONE_EAGER = re.compile(r"@(ManyToOne|OneToOne)\s*(\([^)]*\))?")
RE_RESPONSE_LONG_ID = re.compile(r"record\s+\w*(Response|Dto|DTO|Summary)\s*\([^)]*\blong\s+id\b")
RE_JSON_STRING = re.compile(r"JsonFormat\s*\(\s*shape\s*=\s*JsonFormat\.Shape\.STRING|ToStringSerializer")

# ---------- config ----------
RE_YAML_KV = re.compile(r"^(\s*)([\w.\-\[\]]+)\s*:\s*(.*)$")
SECRET_KEY = re.compile(r"(password|secret|api[-_]?key|token|private[-_]?key|client[-_]?secret)$", re.I)
PLACEHOLDER = re.compile(r"^\s*(\$\{|\"?\$\{|''|\"\"|null|~|change[-_]?me|<|\{cipher\}|file:|classpath:)", re.I)
RE_PROP_KV = re.compile(r"^\s*([\w.\-\[\]]+)\s*[=:]\s*(.*)$")


@dataclass
class Hit:
    area: str
    check: str
    severity: str
    file: str
    line: int
    text: str


def walk(root: str) -> tuple[list[str], list[str], list[str]]:
    java, cfg, build = [], [], []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            p = os.path.join(dp, f)
            if f.endswith(".java"):
                java.append(p)
            elif re.match(r"application(-[\w]+)?\.(ya?ml|properties)$", f) or f in ("bootstrap.yml", "bootstrap.yaml"):
                cfg.append(p)
            elif f in ("pom.xml", "build.gradle", "build.gradle.kts"):
                build.append(p)
    return sorted(java), sorted(cfg), sorted(build)


def read(p: str) -> str:
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def snippet(text: str, idx: int) -> str:
    ln = line_of(text, idx)
    return text.split("\n")[ln - 1].strip()[:120]


def is_test_path(rel: str) -> bool:
    return "/src/test/" in "/" + rel.replace("\\", "/")


# ---------------- build ----------------
def scan_build(root: str, files: list[str], hits: list[Hit]) -> dict:
    info = {"boot": None, "java": None, "jpa": False, "security": False}
    for p in files:
        rel = os.path.relpath(p, root)
        t = read(p)
        m = (re.search(r"<parent>.*?spring-boot-starter-parent.*?<version>([\d.]+)</version>", t, re.S)
             or re.search(r"org\.springframework\.boot['\"]?\)?\s+version\s+['\"]([\d.]+)['\"]", t)
             or re.search(r"spring-boot-dependencies.*?<version>([\d.]+)</version>", t, re.S))
        if m:
            ver = m.group(1)
            line = ".".join(ver.split(".")[:2])
            info["boot"] = ver
            end = BOOT_OSS_END.get(line)
            ln = line_of(t, m.start())
            if end and end < TODAY:
                hits.append(Hit("build", "spring_boot_unsupported", "HIGH", rel, ln,
                                f"Spring Boot {ver}: OSS support for {line}.x ended {end} — no CVE fixes; migrate (4.1.x current)"))
            elif end:
                hits.append(Hit("build", "spring_boot_line", "INFO", rel, ln, f"Spring Boot {ver}: OSS support until {end}"))
            else:
                hits.append(Hit("build", "spring_boot_line", "INFO", rel, ln, f"Spring Boot {ver}: line not in the support table — check endoflife.date/spring-boot"))
        j = (re.search(r"<(java\.version|maven\.compiler\.release)>\s*([\d.]+)\s*<", t)
             or re.search(r"languageVersion\s*(=|\.set\()\s*JavaLanguageVersion\.of\(\s*(\d+)\s*\)", t)
             or re.search(r"sourceCompatibility\s*=\s*['\"]?([\d.]+)", t))
        if j:
            jv = j.group(2) if j.lastindex and j.lastindex >= 2 else j.group(1)
            info["java"] = jv
            sev = "INFO" if jv in ("21", "25") else "LOW"
            hits.append(Hit("build", "java_release", sev, rel, line_of(t, j.start()),
                            f"Java {jv}" + ("" if sev == "INFO" else " — not an LTS the skill targets (21 / 25)")))
        info["jpa"] = info.get("jpa") or ("spring-boot-starter-data-jpa" in t or "hibernate" in t)
        info["security"] = info.get("security") or ("spring-boot-starter-security" in t or "spring-security" in t)
        if "flyway" not in t and "liquibase" not in t:
            hits.append(Hit("build", "no_migration_tool", "MEDIUM" if info["jpa"] else "LOW", rel, 1,
                            "neither Flyway nor Liquibase in the build — fine only if the schema is versioned elsewhere (e.g. Supabase migrations)"))
        if not info["security"] and "spring-boot-starter-web" in t:
            hits.append(Hit("build", "no_spring_security", "MEDIUM", rel, 1,
                            "spring-boot-starter-web without spring-boot-starter-security — every endpoint is open unless another gate (gateway, RLS-bound DB role) is proven"))
    return info


# ---------------- config ----------------
def flatten_yaml(text: str) -> list[tuple[str, str, int]]:
    """Very small YAML flattener for key: value trees (no lists of maps)."""
    out: list[tuple[str, str, int]] = []
    stack: list[tuple[int, str]] = []
    for i, raw in enumerate(text.split("\n"), start=1):
        line = raw.split(" #")[0].rstrip()
        if not line.strip() or line.strip().startswith("#") or line.strip() == "---":
            if line.strip() == "---":
                stack = []
            continue
        m = RE_YAML_KV.match(line)
        if not m:
            continue
        indent, key, val = len(m.group(1)), m.group(2), m.group(3).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = ".".join([k for _, k in stack] + [key])
        if val == "":
            stack.append((indent, key))
        else:
            out.append((path, val.strip("'\""), i))
    return out


def scan_config(root: str, files: list[str], hits: list[Hit], jpa: bool = True) -> None:
    for p in files:
        rel = os.path.relpath(p, root)
        local = bool(LOCAL_PROFILE.search(os.path.basename(p))) or is_test_path(rel)
        t = read(p)
        if p.endswith((".yml", ".yaml")):
            kvs = flatten_yaml(t)
        else:
            kvs = []
            for i, raw in enumerate(t.split("\n"), start=1):
                m = RE_PROP_KV.match(raw)
                if m and not raw.strip().startswith(("#", "!")):
                    kvs.append((m.group(1), m.group(2).strip(), i))
        keys = {k: (v, ln) for k, v, ln in kvs}

        def get(k: str):
            return keys.get(k)

        oiv = get("spring.jpa.open-in-view")
        if jpa and not local and (oiv is None or oiv[0].lower() != "false"):
            hits.append(Hit("config", "open_in_view_not_false", "MEDIUM", rel, oiv[1] if oiv else 1,
                            "spring.jpa.open-in-view is not false (default true holds a DB connection during JSON serialisation)"))
        ddl = get("spring.jpa.hibernate.ddl-auto")
        if ddl and ddl[0].lower() in ("update", "create", "create-drop"):
            hits.append(Hit("config", "ddl_auto_mutating", "LOW" if local else "HIGH", rel, ddl[1],
                            f"ddl-auto={ddl[0]} — schema changes belong in migrations; use validate"))
        for k, want, check in (("server.error.include-stacktrace", "never", "stacktrace_in_errors"),
                               ("server.error.include-message", "never", "message_in_errors")):
            v = get(k)
            if not local and (v is None or v[0].lower() != want):
                hits.append(Hit("config", check, "LOW", rel, v[1] if v else 1, f"{k} is not '{want}'"))
        exp = get("management.endpoints.web.exposure.include")
        if exp:
            vals = {x.strip() for x in exp[0].split(",")}
            risky = vals & {"*", "env", "heapdump", "configprops", "loggers", "beans", "threaddump", "shutdown"}
            if risky:
                hits.append(Hit("config", "actuator_exposure", "HIGH", rel, exp[1], f"actuator exposes {sorted(risky)} — health (+info/prometheus behind auth) only"))
        h2 = get("spring.h2.console.enabled")
        if h2 and h2[0].lower() == "true":
            hits.append(Hit("config", "h2_console_enabled", "LOW" if local else "MEDIUM", rel, h2[1], "H2 console enabled"))
        sw = get("springdoc.swagger-ui.enabled")
        if not local and sw and sw[0].lower() == "true":
            hits.append(Hit("config", "swagger_ui_enabled", "LOW", rel, sw[1], "Swagger UI enabled outside the local profile"))
        for k, v, ln in kvs:
            leaf = k.split(".")[-1]
            if SECRET_KEY.search(leaf) and v and not PLACEHOLDER.match(v):
                hits.append(Hit("config", "literal_secret", "LOW" if local else "HIGH", rel, ln, f"{k} has a literal value — use ${{ENV_VAR}} or a vault"))


# ---------------- java ----------------
def scan_java(root: str, files: list[str], hits: list[Hit]) -> dict:
    texts = {p: read(p) for p in files}
    entities: set[str] = set()
    for p, t in texts.items():
        for m in RE_ENTITY_CLASS.finditer(RE_COMMENT.sub("", t)):
            entities.add(m.group(1))
    entity_ret = re.compile(r"(?:public\s+|^\s*)(?:ResponseEntity<\s*)?(?:List<|Page<|Set<|Optional<|Collection<)?\s*(" + "|".join(sorted(map(re.escape, entities))) + r")\b[\s>]*\s+\w+\s*\(", re.M) if entities else None
    stats = {"java_files": len(files), "entities": len(entities), "controllers": 0}
    for p, raw in texts.items():
        rel = os.path.relpath(p, root)
        test = is_test_path(rel)
        t = RE_COMMENT.sub(lambda m: " " * len(m.group(0)), raw)  # keep offsets
        add = lambda check, sev, idx: hits.append(Hit("java", check, sev, rel, line_of(t, idx), snippet(raw, idx)))

        for m in RE_STRING_CONCAT_QUERY.finditer(t):
            add("query_built_by_concatenation", "CRITICAL", m.start())
        if RE_REST_CONTROLLER.search(t):
            stats["controllers"] += 1
            if entity_ret:
                for m in entity_ret.finditer(t):
                    add("entity_returned_from_controller", "HIGH", m.start())
            for m in RE_REQUEST_BODY.finditer(t):
                seg = t[max(0, m.start() - 60): m.end() + 40]
                if not RE_VALID.search(seg):
                    add("request_body_without_valid", "MEDIUM", m.start())
        for m in RE_CSRF_DISABLE.finditer(t):
            add("csrf_disabled", "LOW" if RE_STATELESS.search(t) else "HIGH", m.start())
        for m in RE_PERMIT_ALL_EVERYTHING.finditer(t):
            add("permit_all_everything", "HIGH", m.start())
        if RE_CORS_CREDENTIALS.search(t) and RE_CORS_WILDCARD.search(t):
            add("cors_credentials_with_wildcard", "HIGH", RE_CORS_WILDCARD.search(t).start())
        if not test:
            for m in RE_FIELD_AUTOWIRED.finditer(t):
                add("field_injection", "MEDIUM", m.start())
        if RE_DATA_ON_ENTITY.search(t):
            add("lombok_data_on_entity", "HIGH", RE_DATA_ON_ENTITY.search(t).start())
        for m in RE_SWALLOWED.finditer(t):
            add("swallowed_exception", "MEDIUM", m.start())
        for m in RE_SORT_BY_VAR.finditer(t):
            add("sort_by_variable_verify_whitelist", "MEDIUM", m.start())
        if RE_SECURITY_CONTEXT_FILE.search(os.path.basename(p)) or RE_SECURITY_CONTEXT_FILE.search(t[:2000]):
            for m in RE_RANDOM.finditer(t):
                add("java_util_random_in_security_context", "HIGH", m.start())
        if not test:
            for m in RE_OPTIONAL_FIELD_PARAM.finditer(t):
                add("optional_as_field_or_parameter", "LOW", m.start())
            for m in RE_SYSOUT.finditer(t):
                add("sysout_or_printstacktrace", "LOW", m.start())
        for m in RE_TOONE_EAGER.finditer(t):
            if "LAZY" not in (m.group(2) or ""):
                add("to_one_without_lazy", "LOW", m.start())
        for m in RE_RESPONSE_LONG_ID.finditer(t):
            if not RE_JSON_STRING.search(t):
                add("long_id_in_response_without_string_shape", "LOW", m.start())
    return stats


def summary(hits: list[Hit], info: dict, jstats: dict, n_cfg: int) -> str:
    def n(check: str) -> int:
        return sum(1 for h in hits if h.check == check)
    return "\n".join([
        f"Build: Spring Boot {info.get('boot') or '?'}, Java {info.get('java') or '?'}; "
        f"{jstats['java_files']} Java files, {jstats['entities']} entities, {jstats['controllers']} controllers, {n_cfg} config files",
        f"Blockers: {n('query_built_by_concatenation')} string-built queries, {n('entity_returned_from_controller')} entities returned from controllers, "
        f"{n('csrf_disabled')} csrf disabled, {n('permit_all_everything')} permitAll-everything, {n('cors_credentials_with_wildcard')} CORS wildcard+credentials, "
        f"{n('literal_secret')} literal secrets, {n('actuator_exposure')} actuator exposures, {n('spring_boot_unsupported')} unsupported Boot line",
        f"Design: {n('request_body_without_valid')} bodies without @Valid, {n('field_injection')} field injections, {n('lombok_data_on_entity')} @Data entities, "
        f"{n('swallowed_exception')} swallowed exceptions, {n('sort_by_variable_verify_whitelist')} Sort.by(variable), {n('open_in_view_not_false')} open-in-view, {n('ddl_auto_mutating')} ddl-auto",
        f"Polish: {n('optional_as_field_or_parameter')} Optional misuse, {n('sysout_or_printstacktrace')} sysout/printStackTrace, {n('to_one_without_lazy')} eager ToOne, "
        f"{n('long_id_in_response_without_string_shape')} long ids, {n('stacktrace_in_errors') + n('message_in_errors')} error-detail settings",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=SEVERITIES[1:])
    ap.add_argument("--max-hits", type=int, default=60)
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    java, cfg, build = walk(root)
    hits: list[Hit] = []
    info = scan_build(root, build, hits)
    scan_config(root, cfg, hits, jpa=bool(info.get("jpa")))
    jstats = scan_java(root, java, hits)
    hits.sort(key=lambda h: (-SEVERITIES.index(h.severity), h.area, h.file, h.line))
    if a.json:
        print(json.dumps({"root": root, "build": info, "stats": jstats, "hits": [asdict(h) for h in hits],
                          "summary": summary(hits, info, jstats, len(cfg))}, indent=2))
    else:
        print(f"java_scan: {root}\n")
        for h in hits[: a.max_hits]:
            print(f"  [{h.severity}] {h.check}  {h.file}:{h.line}  {h.text}")
        if len(hits) > a.max_hits:
            print(f"  ... {len(hits) - a.max_hits} more (--max-hits / --json)")
        print("\n" + summary(hits, info, jstats, len(cfg)))
    if a.fail_on and any(SEVERITIES.index(h.severity) >= SEVERITIES.index(a.fail_on) for h in hits):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
