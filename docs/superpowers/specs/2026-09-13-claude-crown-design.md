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
