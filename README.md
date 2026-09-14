# Claude Crown

Personal Claude Code skill library. One plugin, one namespace: `claude-crown:<skill>`.
Ships a router skill and a SessionStart hook. Holds exactly three domain skills: `scroll-world`, `taste-skill`, `seo-optimizer`.

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

Private use only. Check upstream licenses before any redistribution.
