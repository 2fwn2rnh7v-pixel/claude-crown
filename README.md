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
5. Bump `version` in `.claude-plugin/plugin.json`. Without a bump, `claude plugin update` reports "already latest" and the cached copy stays stale.
6. From `Desktop`: `claude plugin marketplace update claude-crown` then `claude plugin update claude-crown@claude-crown`.
7. Restart Claude Code. The skill appears as `claude-crown:<folder-name>`.

The router (`skills/using-claude-crown/SKILL.md`) needs no edit when skills are added.

## Skills

| Domain | Skill | Description |
|---|---|---|
| Frontend (taste-skill family) | `brandkit` | Premium brand-kit image generation skill for creating high-end brand-guidelines boards, logo systems, identity |
| Frontend (taste-skill family) | `industrial-brutalist-ui` | Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics. Rigid grids, extre |
| Frontend | `frontend-design` | Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps w |
| Frontend (taste-skill family) | `gpt-taste` | Elite UX/UI & Advanced GSAP Motion Engineer. Enforces Python-driven true randomization for layout variance, st |
| Frontend (taste-skill family) | `image-to-code` | Elite website image-to-code skill for Codex. For visually important web tasks, it must first generate the desi |
| Frontend (taste-skill family) | `imagegen-frontend-mobile` | Elite mobile app image-generation skill for creating premium, app-native screen concepts and flows. Designed f |
| Frontend (taste-skill family) | `imagegen-frontend-web` | Elite frontend image-direction skill for generating premium, conversion-aware website design references. CRITI |
| Frontend | `impeccable` | Use when the user wants to design, redesign, shape, critique, audit, polish, clarify, distill, harden, optimiz |
| Frontend (taste-skill family) | `minimalist-ui` | Clean editorial-style interfaces. Warm monochrome palette, typographic contrast, flat bento grids, muted paste |
| Frontend (taste-skill family) | `full-output-enforcement` | Overrides default LLM truncation behavior. Enforces complete code generation, bans placeholder patterns, and h |
| Frontend (taste-skill family) | `redesign-existing-projects` | Upgrades existing websites and apps to premium quality. Audits current design, identifies generic AI patterns, |
| Frontend | `scroll-world` | Scroll-scrubbed "fly through the world" landing page with Higgsfield scenes and a portable scrub engine. |
| SEO | `seo-optimizer` | Audits, fixes and future-proofs website SEO against Google Search Essentials and 2026 AI search, script-backed. |
| Frontend (taste-skill family) | `high-end-visual-design` | Teaches the AI to design like a high-end agency. Defines the exact fonts, spacing, shadows, card structures, a |
| Frontend (taste-skill family) | `stitch-design-taste` | Semantic Design System Skill for Google Stitch. Generates agent-friendly DESIGN.md files that enforce premium, |
| Frontend | `design-taste-frontend` | Anti-slop frontend skill for landing pages, portfolios, and redesigns. The agent reads the brief, infers the r |
| Frontend (taste-skill family) | `design-taste-frontend-v1` | The original v1 taste-skill, preserved for projects depending on its exact behavior. The current default is `d |
| Router | `using-claude-crown` | Use when starting any conversation - establishes how to find and use Claude Crown skills, requiring skill invo |

Invocation name is the **folder** name: `skills/taste-skill/` is invoked as `claude-crown:taste-skill`, whatever its frontmatter `name` says (measured 2026-09-13, Claude Code 2.1.270).
Add a row per skill you drop in. Source and license per vendored skill: see Credits.

## Layout

    .claude-plugin/plugin.json      manifest
    .claude-plugin/marketplace.json local marketplace, source "./"
    skills/                         one folder per skill
    agents/                         impeccable's four subagents
    hooks/                          SessionStart (Crown router) + PostToolUse/Stop (impeccable)
    docs/superpowers/               spec and plan

## Test

    bash hooks/test-session-start.sh

## Credits

| Vendored | Source | Version | License |
|---|---|---|---|
| `hooks/run-hook.cmd`, `hooks/session-start` shape | [obra/superpowers](https://github.com/obra/superpowers) | 6.3.0 | MIT |
| `scroll-world` | scroll-world plugin (cyw) | 0.3.0 | MIT, `skills/scroll-world/LICENSE` |
| `taste-skill` + 12 sibling skills | taste-skill plugin (Leonxlnx) | 1.0.0 | MIT, `skills/taste-skill/LICENSE` |
| `impeccable` + `agents/` + PostToolUse/Stop hooks | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | 4.0.2 | see upstream, no LICENSE file shipped |
| `frontend-design` | anthropics/skills | as installed 2026-07 | `skills/frontend-design/LICENSE.txt` |
| `seo-optimizer` | owner-authored | 2026-09-13 snapshot | owner |

Private use only. Check upstream licenses before any redistribution.
