# Claude Crown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an installable Claude Code plugin `claude-crown` that carries a router skill and a SessionStart hook, ready to receive the owner's skills in `skills/`.

**Architecture:** One repository at `C:\Users\wille\Desktop\claude-crown\` is both marketplace and plugin (`source: "./"`). The only authored skill is the router `using-claude-crown`; a bash SessionStart hook injects its text as `additionalContext`, using the superpowers polyglot `run-hook.cmd` wrapper so it runs on Windows via Git Bash.

**Tech Stack:** Claude Code 2.1.270 plugin system, JSON manifests, Markdown skill with YAML frontmatter, bash + cmd polyglot hook, git, gh CLI.

**Spec:** `docs/superpowers/specs/2026-09-13-claude-crown-design.md`

## Global Constraints

- Plugin `name` is `claude-crown`, kebab-case, `displayName` "Claude Crown", `version` "0.1.0".
- Marketplace `name` is `claude-crown`; single plugin entry with `"source": "./"`.
- No domain skills are authored or copied. `skills/` contains only `using-claude-crown/` until the owner adds folders.
- No agents, commands, MCP servers, output styles, LSP servers, `~~` placeholders.
- `~/.claude/skills/`, `Wythropus/.claude/skills/`, `Wythropus/CLAUDE.md` are not modified.
- Hook fires on `startup|clear|compact`, `shell: bash`, `async: false`; exits 0 silently when no bash is found.
- Windows paths in `claude plugin` commands use forward slashes: `./claude-crown`.
- All shell commands below run in Git Bash (`Bash` tool). `cmd //c` invokes cmd.exe from Git Bash.
- Commits: Conventional Commits, end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

### Task 1: Manifests and repo hygiene

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `.gitignore`

**Interfaces:**
- Produces: plugin name `claude-crown` and marketplace name `claude-crown` that Task 5 installs as `claude-crown@claude-crown`.

- [ ] **Step 1: Run the validator on the empty plugin to see it fail**

Run: `cd /c/Users/wille/Desktop/claude-crown && claude plugin validate ./`
Expected: non-zero exit, message that no manifest / `.claude-plugin/plugin.json` was found.

- [ ] **Step 2: Write plugin.json**

```json
{
  "name": "claude-crown",
  "displayName": "Claude Crown",
  "version": "0.1.0",
  "description": "Personal skill library: security, frontend, backend, selling, SEO, SQL. Router skill plus SessionStart hook, superpowers-shaped.",
  "author": {
    "name": "Marvin Willers"
  },
  "license": "UNLICENSED",
  "keywords": [
    "skills",
    "library",
    "router",
    "security",
    "frontend",
    "backend",
    "seo",
    "sql",
    "selling"
  ]
}
```

- [ ] **Step 3: Write marketplace.json**

```json
{
  "name": "claude-crown",
  "owner": {
    "name": "Marvin Willers"
  },
  "plugins": [
    {
      "name": "claude-crown",
      "source": "./",
      "description": "Personal skill library with router and SessionStart hook"
    }
  ]
}
```

- [ ] **Step 4: Write .gitignore**

```
.DS_Store
Thumbs.db
*.plugin
*.zip
```

- [ ] **Step 5: Validate**

Run: `cd /c/Users/wille/Desktop/claude-crown && claude plugin validate ./`
Expected: exit 0, output contains the plugin name `claude-crown`, no errors. Warnings about an empty `skills/` dir are acceptable at this point.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/wille/Desktop/claude-crown
git add .claude-plugin .gitignore
git commit -m "feat: add plugin and marketplace manifests

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Router skill `using-claude-crown`

**Files:**
- Create: `skills/using-claude-crown/SKILL.md`

**Interfaces:**
- Produces: `skills/using-claude-crown/SKILL.md`, read verbatim by Task 3's hook. The line `Claude Crown is a personal skill library.` must exist in the body; Task 3 and Task 5 grep for it.

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: using-claude-crown
description: Use when starting any conversation - establishes how to find and use Claude Crown skills, requiring skill invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

# Using Claude Crown

Claude Crown is a personal skill library. Every skill in it is namespaced `claude-crown:<name>`.
This skill says how to pick from that library. It adds to other rules (project CLAUDE.md, other
plugins), it does not replace them. Direct user instructions and CLAUDE.md win over this skill.

## The Rule

Before any response or action, including clarifying questions, exploring files, or reading code:

1. Scan the available skills list for every entry prefixed `claude-crown:`.
2. Match each description against the request. If there is even a 1% chance a skill applies,
   invoke it via the Skill tool. Invoke, do not suggest, do not ask.
3. Multiple matches are the norm. Invoke all of them.
4. Process-shaped skills first (planning, review, debugging, security review), then
   implementation-shaped skills (frontend, backend, SQL, copy).
5. Announce compactly, one line: `Crown: <skill-a>, <skill-b>. Go.` Then execute the task with
   the loaded skills.
6. A skill that turns out not to fit can be dropped after reading it. Reading is cheap,
   guessing is not.

## Red Flags

| Thought | Reality |
|---|---|
| "Just a simple question" | Questions are tasks. Check the list. |
| "I need context first" | Skill check comes before exploring. |
| "I remember this skill" | Skills change. Read the current version. |
| "Overkill for this" | Simple things grow. Load it. |
| "Only one skill fits" | Look again. One is the minimum, not the target. |
| "I'll suggest it and let the user decide" | Invoke. The library was installed to be used. |
| "No Crown skill matches" | Say so in one line, then proceed. Do not force a fit. |
| "CLAUDE.md already covers this" | CLAUDE.md wins on conflict. Where it is silent, Crown applies. |

## Adding a skill

Drop `skills/<kebab-name>/SKILL.md` into the plugin. Frontmatter needs `name` and
`description` (third person, with the phrases a user would say). Optional folders:
`references/`, `scripts/`, `assets/`. Then run `claude plugin validate <plugin-path>` and
restart Claude Code. Nothing in this file needs editing when a skill is added.
```

- [ ] **Step 2: Validate**

Run: `cd /c/Users/wille/Desktop/claude-crown && claude plugin validate ./ --strict`
Expected: exit 0, skill `using-claude-crown` listed or no complaint about `skills/`.

- [ ] **Step 3: Frontmatter check**

Run: `head -4 /c/Users/wille/Desktop/claude-crown/skills/using-claude-crown/SKILL.md`
Expected: line 1 `---`, line 2 starts `name: using-claude-crown`, line 3 starts `description: Use when starting any conversation`, line 4 `---`.

- [ ] **Step 4: Commit**

```bash
cd /c/Users/wille/Desktop/claude-crown
git add skills/using-claude-crown/SKILL.md
git commit -m "feat: add using-claude-crown router skill

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: SessionStart hook

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/run-hook.cmd`
- Create: `hooks/session-start` (no extension, executable bit set)
- Create: `hooks/test-session-start.sh`

**Interfaces:**
- Consumes: `skills/using-claude-crown/SKILL.md` from Task 2.
- Produces: stdout JSON `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}` where `additionalContext` starts with `<EXTREMELY_IMPORTANT>\nYou have Claude Crown.` Task 5 greps a live session for `You have Claude Crown`.

- [ ] **Step 1: Write the failing test script**

Create `hooks/test-session-start.sh` (kept in repo, it is the hook's test):

```bash
#!/usr/bin/env bash
# Test: session-start emits valid JSON whose additionalContext carries the router text.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"

out="$(CLAUDE_PLUGIN_ROOT="$ROOT" bash "${HERE}/session-start")"

printf '%s' "$out" | node -e '
  const raw = require("fs").readFileSync(0, "utf8");
  const j = JSON.parse(raw);
  const ctx = j.hookSpecificOutput && j.hookSpecificOutput.additionalContext;
  if (j.hookSpecificOutput.hookEventName !== "SessionStart") { console.error("FAIL: hookEventName"); process.exit(1); }
  if (!ctx || !ctx.startsWith("<EXTREMELY_IMPORTANT>\nYou have Claude Crown.")) { console.error("FAIL: context prefix"); process.exit(1); }
  if (!ctx.includes("Claude Crown is a personal skill library.")) { console.error("FAIL: router body missing"); process.exit(1); }
  if (!ctx.trimEnd().endsWith("</EXTREMELY_IMPORTANT>")) { console.error("FAIL: context suffix"); process.exit(1); }
  console.log("PASS: session-start JSON ok, " + ctx.length + " chars");
'
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd /c/Users/wille/Desktop/claude-crown && bash hooks/test-session-start.sh`
Expected: FAIL, `session-start: No such file or directory`.

- [ ] **Step 3: Write hooks.json**

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

- [ ] **Step 4: Write run-hook.cmd**

Copied from superpowers 6.3.0 `hooks/run-hook.cmd` (MIT, Jesse Vincent), with an attribution line added. Content:

```
: << 'CMDBLOCK'
@echo off
REM Cross-platform polyglot wrapper for hook scripts.
REM Adapted from obra/superpowers hooks/run-hook.cmd (MIT).
REM On Windows: cmd.exe runs the batch portion, which finds and calls bash.
REM On Unix: the shell interprets this as a script (: is a no-op in bash).
REM
REM Hook scripts use extensionless filenames (e.g. "session-start" not
REM "session-start.sh") so Claude Code's Windows auto-detection -- which
REM prepends "bash" to any command containing .sh -- doesn't interfere.
REM
REM Usage: run-hook.cmd <script-name> [args...]

if "%~1"=="" (
    echo run-hook.cmd: missing script name >&2
    exit /b 1
)

set "HOOK_DIR=%~dp0"

if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    "C:\Program Files (x86)\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

where bash >nul 2>nul
if %ERRORLEVEL% equ 0 (
    bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)

REM No bash found - exit silently rather than error
exit /b 0
CMDBLOCK

# Unix: run the named script directly
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```

- [ ] **Step 5: Write session-start**

```bash
#!/usr/bin/env bash
# SessionStart hook for the claude-crown plugin.
# Injects the using-claude-crown router skill as additional context.
# Adapted from obra/superpowers hooks/session-start (MIT); Claude Code branch only.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROUTER="${PLUGIN_ROOT}/skills/using-claude-crown/SKILL.md"

if [ -r "$ROUTER" ]; then
  router_content="$(cat "$ROUTER")"
else
  router_content="Error: router skill not readable at ${ROUTER}. Invoke claude-crown:using-claude-crown via the Skill tool."
fi

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

router_escaped="$(escape_for_json "$router_content")"
session_context="<EXTREMELY_IMPORTANT>\nYou have Claude Crown.\n\n**Below is the full content of your 'claude-crown:using-claude-crown' skill - your introduction to using the Claude Crown skill library. For all other skills, use the 'Skill' tool:**\n\n${router_escaped}\n</EXTREMELY_IMPORTANT>"

# printf instead of heredoc: bash 5.3+ heredoc hang, see obra/superpowers#571
printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$session_context"

exit 0
```

- [ ] **Step 6: Set executable bit and run the test**

Run: `cd /c/Users/wille/Desktop/claude-crown && chmod +x hooks/session-start hooks/test-session-start.sh && bash hooks/test-session-start.sh`
Expected: `PASS: session-start JSON ok, N chars` with N above 2000.

- [ ] **Step 7: Run through the cmd wrapper, the path Claude Code takes on Windows**

Run: `cd /c/Users/wille/Desktop/claude-crown && CLAUDE_PLUGIN_ROOT="$(pwd -W)" cmd //c "hooks\\run-hook.cmd" session-start | node -e 'const j=JSON.parse(require("fs").readFileSync(0,"utf8")); console.log(j.hookSpecificOutput.additionalContext.slice(0,60))'`
Expected: prints `<EXTREMELY_IMPORTANT>` followed by `You have Claude Crown.`

- [ ] **Step 8: Validate**

Run: `cd /c/Users/wille/Desktop/claude-crown && claude plugin validate ./ --strict`
Expected: exit 0, hooks config recognized, no unknown-field warnings.

- [ ] **Step 9: Commit**

```bash
cd /c/Users/wille/Desktop/claude-crown
git add hooks
git update-index --chmod=+x hooks/session-start hooks/test-session-start.sh
git commit -m "feat: add SessionStart hook injecting the router skill

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: install commands from Task 1, drop-in contract from Task 2.

- [ ] **Step 1: Write README.md**

```markdown
# Claude Crown

Personal Claude Code skill library. One plugin, one namespace: `claude-crown:<skill>`.
Ships a router skill and a SessionStart hook. Domain skills are added by the owner.

## Install (local marketplace)

From the folder that contains `claude-crown/` (forward slashes on Windows):

    claude plugin marketplace add ./claude-crown
    claude plugin install claude-crown@claude-crown

Update after changes:

    claude plugin marketplace update claude-crown
    claude plugin update claude-crown@claude-crown

## Adding a skill

1. Create `skills/<kebab-name>/SKILL.md`.
2. Frontmatter: `name` (kebab-case) and `description` (third person, with trigger phrases).
3. Optional: `references/`, `scripts/`, `assets/` next to `SKILL.md`.
4. `claude plugin validate ./claude-crown --strict`
5. Restart Claude Code. The skill appears as `claude-crown:<name>`.

The router (`skills/using-claude-crown/SKILL.md`) needs no edit when skills are added.

## Skills

| Domain | Skill | Description |
|---|---|---|
| Router | `using-claude-crown` | Loads at session start. Picks Crown skills before any task. |

Add a row per skill you drop in.

## Layout

    .claude-plugin/plugin.json      manifest
    .claude-plugin/marketplace.json local marketplace, source "./"
    skills/                         one folder per skill
    hooks/                          SessionStart hook (bash via Git Bash on Windows)
    docs/superpowers/               spec and plan

## Credits

`hooks/run-hook.cmd` and the shape of `hooks/session-start` come from
[obra/superpowers](https://github.com/obra/superpowers) (MIT).
```

- [ ] **Step 2: Commit**

```bash
cd /c/Users/wille/Desktop/claude-crown
git add README.md
git commit -m "docs: add README with install and drop-in contract

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Install and verify in a live session

**Files:**
- None created. Uses `claude` CLI and a scratch directory.

**Interfaces:**
- Consumes: plugin from Tasks 1-3, marketplace name `claude-crown`.

- [ ] **Step 1: Negative counter-proof before install**

Run:
```bash
claude plugin list 2>&1 | grep -i crown; echo "exit=$?"
```
Expected: no line, `exit=1`. Plugin not installed yet.

- [ ] **Step 2: Add marketplace and install**

Run:
```bash
cd /c/Users/wille/Desktop
claude plugin marketplace add ./claude-crown
claude plugin install claude-crown@claude-crown
claude plugin list
```
Expected: marketplace added; install reports success; list shows `claude-crown@claude-crown` enabled.

- [ ] **Step 3: Positive proof, fresh print-mode session in a neutral directory**

Run:
```bash
mkdir -p /c/Users/wille/AppData/Local/Temp/crown-check && cd /c/Users/wille/AppData/Local/Temp/crown-check
env -u CLAUDECODE claude -p "Answer with two lines only. Line 1: quote the first sentence after the tag EXTREMELY_IMPORTANT in your context, or NONE. Line 2: list every available skill whose name starts with claude-crown: or NONE." 2>&1 | tee crown-check.txt
grep -c "You have Claude Crown" crown-check.txt
grep -c "claude-crown:using-claude-crown" crown-check.txt
```
Expected: both greps print `1` or more. `env -u CLAUDECODE` lifts the nested-session guard when this runs from inside another Claude Code session. If line 1 says NONE, the hook did not run: check `claude plugin list` for the hook and rerun Task 3 Step 7.

- [ ] **Step 4: Plugin listed**

Run: `claude plugin list | grep -i crown`
Expected: one line containing `claude-crown@claude-crown`.

- [ ] **Step 5: Record results**

Paste the outputs of Steps 1 and 3 into the handover note in Task 7.

---

### Task 6: Private GitHub repository

**Files:**
- Modify: `.claude-plugin/plugin.json` (add `repository`, `homepage`)

**Interfaces:**
- Consumes: gh CLI authenticated for the owner.

- [ ] **Step 1: Check gh auth**

Run: `gh auth status 2>&1 | head -5 && gh api user -q .login`
Expected: `Logged in to github.com`, and the login name printed. Call it `OWNER` below.

- [ ] **Step 2: Create private repo and push**

Run:
```bash
cd /c/Users/wille/Desktop/claude-crown
gh repo create claude-crown --private --source=. --remote=origin --push
git remote -v
```
Expected: repo `https://github.com/OWNER/claude-crown` created, `main` pushed, `origin` set.

- [ ] **Step 3: Add repository fields to plugin.json**

Insert after the `"license"` line:

```json
  "homepage": "https://github.com/OWNER/claude-crown",
  "repository": "https://github.com/OWNER/claude-crown",
```

with `OWNER` replaced by the login from Step 1.

- [ ] **Step 4: Validate and push**

Run:
```bash
cd /c/Users/wille/Desktop/claude-crown
claude plugin validate ./ --strict
git add .claude-plugin/plugin.json
git commit -m "chore: link plugin manifest to GitHub repository

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push
gh repo view --json visibility,url -q '.visibility + " " + .url'
```
Expected: validate exit 0; push succeeds; last line prints `PRIVATE https://github.com/OWNER/claude-crown`.

---

### Task 7: Wythropus bookkeeping

**Files:**
- Create: `C:\Users\wille\Desktop\Wythropus\Company\Context\Uebergabe-Claude-Crown-2026-09-13.md`
- Modify: `C:\Users\wille\Desktop\Wythropus\Company\Context\Context.md` (router table, one row)

**Interfaces:**
- Consumes: install lines from Task 1, verification outputs from Task 5, repo URL from Task 6.

- [ ] **Step 1: Write the handover note**

```markdown
---
tags: [context, handover, plugin]
typ: handover
updated: 2026-09-13
---

# Handover — Claude Crown plugin (2026-09-13)

Personal skill library as Claude Code plugin. Lives **outside** this repo.

| Item | Value |
|---|---|
| Path | `C:\Users\wille\Desktop\claude-crown\` |
| Repo | `https://github.com/OWNER/claude-crown` (private) |
| Install | `claude plugin marketplace add ./claude-crown` then `claude plugin install claude-crown@claude-crown`, run from `Desktop` |
| Namespace | `claude-crown:<skill>` |
| Spec | `claude-crown/docs/superpowers/specs/2026-09-13-claude-crown-design.md` |
| Plan | `claude-crown/docs/superpowers/plans/2026-09-13-claude-crown.md` |

## Progress

| Task | State |
|---|---|
| Manifests | done |
| Router skill `using-claude-crown` | done |
| SessionStart hook, tested via cmd wrapper | done |
| README | done |
| Installed, verified in fresh session | done, outputs below |
| Private GitHub repo | done |
| Owner drops domain skills into `skills/` | **open**, owner does this from a separate terminal |
| Re-validate after skills land | open |

## Drop-in contract

`skills/<kebab-name>/SKILL.md`, frontmatter `name` + `description`. Optional `references/`,
`scripts/`, `assets/`. Then `claude plugin validate ./claude-crown --strict`, restart.

## Verification record

(paste Task 5 Step 1 and Step 3 outputs here)

## Not touched

`~/.claude/skills/`, `Wythropus/.claude/skills/`, `CLAUDE.md`. Crown adds a router, the
project rules in CLAUDE.md still win on conflict.
```

- [ ] **Step 2: Add router row to Context.md**

Insert into the table in `Company/Context/Context.md`, after the row `| Why no more Next.js for the connection? | ... |`:

```
| Where is the skill library plugin, how do I add a skill? | [[Uebergabe-Claude-Crown-2026-09-13]] |
```

Frontmatter `updated:` already reads `2026-09-13`, leave it.

- [ ] **Step 3: Verify the link resolves**

Run: `ls "/c/Users/wille/Desktop/Wythropus/Company/Context/Uebergabe-Claude-Crown-2026-09-13.md" && grep -c "Uebergabe-Claude-Crown-2026-09-13" "/c/Users/wille/Desktop/Wythropus/Company/Context/Context.md"`
Expected: file path printed, grep count `1`.

No commit: `Wythropus/` root is not a git repository.
