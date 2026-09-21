# Claude Crown — Design Spec

Date: 2026-09-13
Status: approved in brainstorming, pending written review

## 1. Purpose

Claude Crown is a Claude Code plugin that packages a personal skill library, in the shape of
`superpowers`: one install, one namespace (`claude-crown:<skill>`), a SessionStart hook that
tells Claude to route every task through the library before acting.

The plugin ships **no domain skills of its own**. All domain skills (Security, Frontend,
Backend, Selling, SEO, SQL, and whatever follows) are supplied by the owner and dropped into
`skills/`. The plugin contributes three things: the manifest, the router skill, and the hook.

## 2. Non-goals

- No copying of skills from `~/.claude/skills/` or any plugin cache.
- No agents, commands, MCP servers, output styles, LSP servers.
- No `~~` connector placeholders. Private use only.
- No static skill catalog. Skill metadata is already in context; a hand-written catalog would
  rot with every new skill. Revisit only if routing quality degrades.
- No migration of existing loose skills. `~/.claude/skills/`, `Wythropus/.claude/skills/`, and
  `Wythropus/CLAUDE.md` stay untouched.

## 3. Layout

```
claude-crown/
  .claude-plugin/
    plugin.json          manifest
    marketplace.json     local marketplace, single entry, source "./"
  skills/
    using-claude-crown/  router skill (only skill authored here)
      SKILL.md
    <owner skills>/      dropped in by the owner, one folder per skill
  hooks/
    hooks.json           SessionStart on startup|clear|compact
    run-hook.cmd         polyglot cmd/bash wrapper (superpowers pattern)
    session-start        bash, injects router text as additionalContext
  docs/superpowers/specs/2026-09-13-claude-crown-design.md
  README.md
  .gitignore
```

Location: `C:\Users\wille\Desktop\claude-crown\`, its own git repository, pushed to a **private** GitHub repository `claude-crown` under the owner account (added 2026-09-13 on owner request).

## 4. Manifest

`.claude-plugin/plugin.json`:

```json
{
  "name": "claude-crown",
  "displayName": "Claude Crown",
  "version": "0.1.0",
  "description": "Personal skill library: security, frontend, backend, selling, SEO, SQL. Router skill plus SessionStart hook, superpowers-shaped.",
  "author": { "name": "Marvin Willers" },
  "license": "UNLICENSED",
  "keywords": ["skills", "library", "router", "security", "frontend", "backend", "seo", "sql", "selling"]
}
```

`.claude-plugin/marketplace.json`:

```json
{
  "name": "claude-crown",
  "owner": { "name": "Marvin Willers" },
  "plugins": [
    {
      "name": "claude-crown",
      "source": "./",
      "description": "Personal skill library with router and SessionStart hook"
    }
  ]
}
```

Install (from `C:\Users\wille\Desktop`, forward slashes required on Windows):

```
claude plugin marketplace add ./claude-crown
claude plugin install claude-crown@claude-crown
```

## 5. Drop-in contract for owner skills

Each skill is `skills/<kebab-name>/SKILL.md` with YAML frontmatter:

- `name`: kebab-case, becomes `claude-crown:<name>`. Falls back to folder name if omitted.
- `description`: third person, states what the skill does and the trigger phrases. This is the
  only text the router sees before invoking.

Optional subfolders: `references/`, `scripts/`, `assets/`. Nothing else is required. Skills are
validated with `claude plugin validate ./claude-crown` after they land, not before.

## 6. Router skill `using-claude-crown`

Mirrors `superpowers:using-superpowers`. Frontmatter description: "Use when starting any
conversation - establishes how to find and use Claude Crown skills, requiring skill invocation
before ANY response including clarifying questions."

Body rules:

1. Before any response or action, including clarifying questions, scan the available skills
   list for entries prefixed `claude-crown:`.
2. Match each skill's description against the prompt. If there is even a small chance a skill
   applies, invoke it via the Skill tool. Invoke, do not suggest.
3. Multiple matches are normal. Invoke all of them. Process skills (planning, review,
   debugging shaped) before implementation skills.
4. Announce compactly: `Crown: <skill-a>, <skill-b>. Go.`
5. Skip this skill when dispatched as a subagent for a specific task.
6. Other libraries (superpowers, caveman, project CLAUDE.md) keep their own rules. Crown adds,
   it does not replace. CLAUDE.md and direct user instructions win over this skill.

Red-flag table copied in spirit from using-superpowers ("just a simple question", "I remember
this skill", "overkill"), kept to eight rows.

## 7. Hook

`hooks/hooks.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
            "shell": "bash",
            "async": false
          }
        ]
      }
    ]
  }
}
```

`run-hook.cmd`: polyglot wrapper, copied from superpowers 6.3.0 (MIT). Finds Git Bash on
Windows, execs bash on Unix, exits 0 silently if no bash.

`session-start`: reads `skills/using-claude-crown/SKILL.md`, JSON-escapes it, prints
`{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<EXTREMELY_IMPORTANT>You have Claude Crown. ... </EXTREMELY_IMPORTANT>"}}`.
Cursor and Copilot branches are dropped. Claude Code only.

Cost: router text is under 60 lines, so injecting the full text is cheaper than a pointer plus a
Skill call every session.

## 8. Error handling

- No bash on the machine: hook exits 0, plugin still works, router reachable via Skill tool.
- Router SKILL.md unreadable: hook prints a one-line error context instead of failing the session.
- Owner skill with broken frontmatter: `claude plugin validate` reports it; the skill is
  skipped by Claude Code, the rest of the plugin loads.

## 9. Verification

Before handing back, all of these are run and their output shown:

1. `claude plugin validate ./claude-crown` exits 0 with the router only.
2. `claude plugin marketplace add ./claude-crown` and `claude plugin install claude-crown@claude-crown` succeed.
3. Fresh `claude -p` session in a scratch directory: SessionStart context contains "You have
   Claude Crown"; `claude-crown:using-claude-crown` appears in the available skills.
4. Negative counter-proof: the same check in a session started **before** install shows neither.
5. After the owner's skills land: step 1 again, plus `claude-crown:<one-owner-skill>` visible.

## 10. Wythropus bookkeeping

- `Company/Context/Uebergabe-Claude-Crown-2026-09-13.md`: progress table, install line, drop-in
  contract pointer.
- One router row in `Company/Context/Context.md`: "Where is the skill library plugin, how do I
  add a skill?" → that note.
- `CLAUDE.md` unchanged.

## Addendum 2026-09-13 — vendored skills (owner decision)

Section 2 "no domain skills" is superseded. On owner request the plugin now vendors:
`scroll-world` (0.3.0), the `taste-skill` family (1.0.0, 13 skills), `impeccable` (4.0.2,
including its four agents and PostToolUse/Stop hooks merged into `hooks/hooks.json`),
`frontend-design` (anthropics), `seo-optimizer` (owner-authored, snapshot). Non-goal "no
agents" is lifted for impeccable only; `agents/` holds nothing else. Originals remain
installed as separate plugins until the owner uninstalls them; while both exist, impeccable's
hooks fire twice and every vendored skill is listed twice.

## Addendum 2026-09-13 (2) — caveman vendored (owner decision)

On owner request the plugin now also vendors `caveman`, `caveman-commit`, `caveman-review` and
`compress` from JuliusBrussee/caveman (commit `92f892f`, MIT), plus its two hooks: SessionStart
`caveman-activate.js` (flag file + rule reminder) and UserPromptSubmit `caveman-mode-tracker.js`.
The tracker got one line: `/claude-crown:caveman <arg>` is normalised to `/caveman <arg>`, so the
Crown invocation name sets the same mode. `compress` was taken from `~/.agents/skills/compress`,
not from the plugin cache — the cache ships `scripts` as a git-symlink text stub that is dead on
Windows. While `caveman@caveman` stays installed, the SessionStart reminder appears twice and the
flag file is written twice; both are idempotent. Version 0.3.0.

## Addendum 2026-09-13 (3) — every plugin skill vendored (owner decision)

Owner instruction: "copy every plugin skill there is in the library and insert it into the repo".
Vendored: superpowers 6.3.0 (14), ui-ux-pro-max 2.6.2 (7, its skills sit in `.claude/skills/`
per its manifest `skills` key), claude-code-setup 1.0.0 (1), codex 1.0.6 (3 knowledge skills),
Claude Desktop account skills from `%APPDATA%\Claude\local-agent-mode-sessions\skills-plugin`
(14, incl. two owner-authored), cowork-plugin-management 0.2.2 (2). Total 63 skills, 17 MB.
Rules applied: skill folders copied verbatim, LICENSE copied into the first skill of each
source, `__pycache__` dropped, CRLF normalised to LF. **Not** vendored: superpowers' SessionStart
hook (Crown's router already does that job), codex runtime/hooks/commands/agent (coupled to its
own plugin root), the disabled official `skill-creator` plugin (the Desktop copy is newer and was
taken), `github` (no skills). `~/.claude/skills/` (42 local skills, not plugins) untouched.
Measured in a fresh session: 62 `claude-crown:*` skills visible to the model; `setup-cowork` is the
63rd and carries `disable-model-invocation: true`, so only the user can invoke it. Version 0.4.0.

## Addendum 2026-09-14 (4) — cut back to three skills (owner decision)

Owner instruction: "Delete all skills besides seo-optimizer, taste-skill, scroll-world". Addenda (1)–(3)
are history: 59 skill folders removed, with them `agents/` (impeccable's four) and the impeccable
PostToolUse/Stop hooks plus the caveman SessionStart/UserPromptSubmit hooks — the originals
`caveman@caveman` and the other plugins still provide those. `using-claude-crown` stays: it is the
router the SessionStart hook reads, not library content. Four folders under `skills/`, 1 MB.
Version 0.5.0.

## Addendum 2026-09-14 (5) — `api-guard` added (owner skill #2)

Owner-authored skill delivered as `~/Downloads/files.zip` (German SKILL.md + 4 references),
translated to English, verified against vendor docs, extended with `scripts/api_scan.py`,
`references/framework-recipes.md` and evals. Same folder installed to `~/.claude/skills/`,
`Wythropus/.claude/skills/` and here. Record: `Wythropus/Company/Context/Uebergabe-Skill-API-Guard-2026-09-14.md`.
Version 0.6.0.

## Addendum 2026-09-14 (6) — owner trio complete: `security-review`, `prompt-verstaendnis`

Owner instruction: "Create three skills with the exact same names. Only English." The three are
the owner-authored skills: `api-guard` (0.6.0) plus the two claude.ai account skills with
`creatorType: user`. Both exports contained only `SKILL.md`; the referenced
`references/security-checklist.md`, `prompt-patterns.md` and `agent-setup.md` were written new
in English from the SKILL.md contracts (OWASP Top 10:2025 mapping verified 2026-09-14). German
trigger words and German prompt examples stay as data. Installed in Crown only — `security-review`
would shadow the built-in `security-review` skill if placed in `~/.claude/skills/`. Version 0.7.0.

## Addendum 2026-09-15 (7) — SQL trio: `sql-king`, `sql-security`, `rls-security`

Owner-authored `.skill` packages from `~/Downloads`, already English and sourced. Claims re-verified
2026-09-15 (Supabase key timeline, Auth token bucket, default grants, `pgrst.db_pre_request`); two
details added. Extended `sql-king` with `scripts/sql_scan.py` (stdlib lint of migrations + client
code, tuned on Phoenix's 35 migrations) and evals. Installed to `~/.claude/skills/`,
`Wythropus/.claude/skills/` and here. Record: `Wythropus/Company/Context/Uebergabe-Skills-SQL-Trio-2026-09-15.md`.
Version 0.8.0.

## Addendum 2026-09-15 (8) — `java-pioneer`

Owner-authored `.skill` (English, 7 references, evals shipped loose). Version claims verified
2026-09-15 (Boot 4.1.1 current, 3.5 OSS ended 2026-06-30, Jackson 3 / Testcontainers 2 / Security 7).
Extended with `scripts/java_scan.py` (build + config + Java lint against the non-negotiables, JPA-aware,
tuned on `site/phoenix-api`) and fixtures. Installed 3× as before. Version 0.9.0.

## Addendum 2026-09-21 (9) — `slop-eater`

Owner-directed skill, written from measurements rather than memory: tesla.com/de_de and apple.com/de
captured 2026-09-21 with playwright-cli (real Chrome channel, headed; headless Chromium gets an Akamai
403) at 1440x900 and 390x844: computed styles of nav, hero, buttons at rest and `:hover`, CSSOM
hover/focus rules, breakpoints, tokens, section heights, `<picture>` sources, full `<head>`. Findings
that overturn the usual assumptions: hero is 660px / image aspect, not 100vh; homepage container is
`tcl-homepage-no-scroll-snapping`; parallax is off; hover is one CSS-variable swap. Four references
(`tesla-measured`, `apple-measured`, `patterns` with React/Tailwind adapters, `head-meta`),
`scripts/slop_scan.py` (stdlib; tuned on `site/app/src`: 8 HIGH leads, 0 false CRITICAL), three evals.
TDD per `writing-skills`: baseline subagent without the skill produced 1 CRITICAL / 21 HIGH (now
`evals/fixtures/bad`); the same brief with the skill loaded is `evals/fixtures/good`. Installed 3x as
before. Version 0.10.0.
