# Claude Crown

Personal Claude Code skill library. One plugin, one namespace: `claude-crown:<skill>`.
Ships a router skill and a SessionStart hook. Holds eleven domain skills: `java-pioneer`, `scroll-world`, `taste-skill`, `slop-eater`, `seo-optimizer`, the owner trio `api-guard`, `security-review`, `prompt-verstaendnis`, and the SQL trio `sql-king`, `sql-security`, `rls-security`.

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
5. Bump `version` in `.claude-plugin/plugin.json`. Without a bump, `claude plugin update` reports "already latest" and the cached copy stays stale.
6. From `Desktop`: `claude plugin marketplace update claude-crown` then `claude plugin update claude-crown@claude-crown`.
7. Restart Claude Code. The skill appears as `claude-crown:<folder-name>`.

The router (`skills/using-claude-crown/SKILL.md`) needs no edit when skills are added.

## Skills

| Domain | Skill | Description |
|---|---|---|
| Frontend | `scroll-world` | Scroll-scrubbed "fly through the world" landing page with Higgsfield scenes and a portable scrub engine. |
| Frontend | `taste-skill` | Anti-slop frontend skill for landing pages, portfolios, and redesigns. The agent reads the brief, infers the r |
| Frontend | `slop-eater` | Builds and audits marketing pages to the measured standard of Tesla.com and Apple.com: hero sizing, variable-swap hover, reveal and sticky scrub, art-directed images, full head block; `scripts/slop_scan.py`. |
| Backend | `java-pioneer` | Expert playbook for writing production-grade Java (21/25 LTS) backends with Spring Boot 4 and connecting them t |
| Database | `sql-king` | Foundation skill for everything involving a cloud database (Postgres / Supabase) in a TypeScript app: q |
| Database | `sql-security` | Securing the database layer of a TypeScript app on Postgres/Supabase — keys, roles, GRANT/REVOKE, ra |
| Database | `rls-security` | Row Level Security in Postgres/Supabase — who may see, create, change and delete an individual row; p |
| Backend | `security-review` | Performs systematic security reviews of code, specialised in TypeScript web applications. 10 categories |
| Process | `prompt-verstaendnis` | Interprets and understands the prompts of a German-speaking developer working on his own app (Agrarmonito |
| Backend | `api-guard` | Audits and hardens API usage in TypeScript web apps: rate limiting and quotas, API keys and paid calls in the |
| SEO | `seo-optimizer` | Audits, fixes and future-proofs website SEO against Google Search Essentials and 2026 AI search, script-backed. |
| Router | `using-claude-crown` | Use when starting any conversation - establishes how to find and use Claude Crown skills, requiring skill invo |

Invocation name is the **folder** name: `skills/taste-skill/` is invoked as `claude-crown:taste-skill`, whatever its frontmatter `name` says (measured 2026-09-13, Claude Code 2.1.270).
Add a row per skill you drop in. Source and license per vendored skill: see Credits.

## Layout

    .claude-plugin/plugin.json      manifest
    .claude-plugin/marketplace.json local marketplace, source "./"
    skills/                         one folder per skill
    hooks/                          SessionStart (Crown router)
    docs/superpowers/               spec and plan

## Test

    bash hooks/test-session-start.sh

## Credits

| Vendored | Source | Version | License |
|---|---|---|---|
| `hooks/run-hook.cmd`, `hooks/session-start` shape | [obra/superpowers](https://github.com/obra/superpowers) | 6.3.0 | MIT |
| `scroll-world` | scroll-world plugin (cyw) | 0.3.0 | MIT, `skills/scroll-world/LICENSE` |
| `taste-skill` | taste-skill plugin (Leonxlnx) | 1.0.0 | MIT, `skills/taste-skill/LICENSE` |
| `seo-optimizer` | owner-authored | 2026-09-13 snapshot | owner |
| `api-guard` | owner-authored, translated and extended 2026-09-14 (script, framework recipes, evals) | 2026-09-14 snapshot | owner |
| `security-review`, `prompt-verstaendnis` | owner-authored claude.ai account skills, translated to English 2026-09-14; their `references/` were missing from the export and written new | 2026-09-14 | owner |
| `sql-king` (+ `scripts/sql_scan.py`, evals), `sql-security`, `rls-security` | owner-authored `.skill` packages, English, verified 2026-09-15 against Supabase/Postgres docs | 2026-09-15 | owner |
| `java-pioneer` (+ `scripts/java_scan.py`, evals) | owner-authored `.skill` package, English, versions verified 2026-09-15 | 2026-09-15 | owner |
| `slop-eater` (+ `scripts/slop_scan.py`, evals, 4 references) | owner-directed, written 2026-09-21 from playwright-cli measurements of tesla.com/de_de and apple.com/de (real Chrome channel); baseline/GREEN tested with subagents | 2026-09-21 | owner |

Private use only. Check upstream licenses before any redistribution.
