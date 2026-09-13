# Claude Crown

Personal Claude Code skill library. One plugin, one namespace: `claude-crown:<skill>`.
Ships a router skill and a SessionStart hook. Every skill from every installed plugin is vendored here (63 skills as of 0.4.0), so the originals can be uninstalled.

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
| Caveman | `caveman` | Ultra-compressed communication mode. Cuts token usage ~75% by speaking like caveman while keeping full technic |
| Caveman | `caveman-commit` | Ultra-compressed commit message generator. Cuts noise from commit messages while preserving intent and reasoni |
| Caveman | `caveman-review` | Ultra-compressed code review comments. Cuts noise from PR feedback while preserving the actionable signal. Eac |
| Caveman | `compress` | Compress natural language memory files (CLAUDE.md, todos, preferences) into caveman format to save input token |
| Process (superpowers) | `brainstorming` | You MUST use this before any creative work - creating features, building components, adding functionality, or  |
| Process (superpowers) | `dispatching-parallel-agents` | Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies |
| Process (superpowers) | `executing-plans` | Use when you have a written implementation plan to execute in a separate session with review checkpoints |
| Process (superpowers) | `finishing-a-development-branch` | Use when implementation is complete, all tests pass, and you need to decide how to integrate the work |
| Process (superpowers) | `receiving-code-review` | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear |
| Process (superpowers) | `requesting-code-review` | Use when completing tasks, implementing major features, or before merging to verify work meets requirements |
| Process (superpowers) | `subagent-driven-development` | Use when executing implementation plans with independent tasks in the current session |
| Process (superpowers) | `systematic-debugging` | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| Process (superpowers) | `test-driven-development` | Use when implementing any feature or bugfix, before writing implementation code |
| Process (superpowers) | `using-git-worktrees` | Use when starting feature work that needs isolation from current workspace or before executing implementation  |
| Process (superpowers) | `using-superpowers` | Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before |
| Process (superpowers) | `verification-before-completion` | Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires runn |
| Process (superpowers) | `writing-plans` | Use when you have a spec or requirements for a multi-step task, before touching code |
| Process (superpowers) | `writing-skills` | Use when creating new skills, editing existing skills, or verifying skills work before deployment |
| Frontend (ui-ux-pro-max) | `banner-design` | Design banners for social media, ads, website heroes, creative assets, and print. Multiple art direction optio |
| Frontend (ui-ux-pro-max) | `brand` | Brand voice, visual identity, messaging frameworks, asset management, brand consistency. Activate for branded  |
| Frontend (ui-ux-pro-max) | `design` | Comprehensive design skill: brand identity, design tokens, UI styling, logo generation (55 styles, Gemini AI), |
| Frontend (ui-ux-pro-max) | `design-system` | Token architecture, component specifications, and slide generation. Three-layer tokens (primitive→semantic→com |
| Frontend (ui-ux-pro-max) | `slides` | Create strategic HTML presentations with Chart.js, design tokens, responsive layouts, copywriting formulas, an |
| Frontend (ui-ux-pro-max) | `ui-styling` | Create beautiful, accessible user interfaces with shadcn/ui components (built on Radix UI + Tailwind), Tailwin |
| Frontend (ui-ux-pro-max) | `ui-ux-pro-max` | UI/UX design intelligence for web and mobile. Includes 50+ styles, 161 color palettes, 57 font pairings, 161 p |
| Tooling | `claude-automation-recommender` | Analyze a codebase and recommend Claude Code automations (hooks, subagents, skills, plugins, MCP servers). Use |
| Tooling (codex) | `codex-cli-runtime` | Internal helper contract for calling the codex-companion runtime from Claude Code |
| Tooling (codex) | `codex-result-handling` | Internal guidance for presenting Codex helper output back to the user |
| Tooling (codex) | `gpt-5-4-prompting` | Internal guidance for composing Codex and GPT-5.4 prompts for coding, review, diagnosis, and research tasks in |
| Documents (anthropic-skills) | `docx` | Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx) or Word tem |
| Documents (anthropic-skills) | `pdf` | Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text |
| Documents (anthropic-skills) | `pptx` | Use this skill any time a .pptx or .potx file is involved in any way — as input, output, or both. This include |
| Documents (anthropic-skills) | `xlsx` | Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user  |
| Desktop (anthropic-skills) | `consolidate-memory` | Reflective pass over your memory files — merge duplicates, fix stale facts, prune the index. |
| Desktop (anthropic-skills) | `explain-usage` | Explain where this session's tokens went, with one simple chart in plain language. Use when the user says thin |
| Desktop (anthropic-skills) | `import-memory` | Import a memory export from another AI assistant into Claude's memory — conversationally, additively, and with |
| Desktop (anthropic-skills) | `morning` | Render the user's morning brief as a styled HTML artifact, or set it up as a recurring weekday task. Use only  |
| Desktop (anthropic-skills) | `schedule` | Create or update a scheduled task that runs automatically. Use when the user says things like \"every day\", \ |
| Desktop (anthropic-skills) | `setup-claude` | Guided setup — install role-matched plugins, connect your tools, try a skill. |
| Desktop (anthropic-skills) | `setup-cowork` | Guided setup — install role-matched plugins, connect your tools, try a skill. |
| Desktop (anthropic-skills) | `skill-creator` | Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to c |
| Owner (claude.ai skills) | `prompt-verstaendnis` | Interpretiert und versteht Nutzer-Prompts eines deutschsprachigen Entwicklers, der an seiner eigenen App (Agra |
| Owner (claude.ai skills) | `security-review` | Führt systematische Sicherheitsüberprüfungen von Code durch — spezialisiert auf TypeScript-Webapplikationen. I |
| Desktop (cowork-plugin-management) | `cowork-plugin-customizer` | Customize a Claude Code plugin for a specific organization's tools and workflows. Use when: customize plugin,  |
| Desktop (cowork-plugin-management) | `create-cowork-plugin` | Guide users through creating a new plugin from scratch in a cowork session. Use when users want to create a pl |
| Router | `using-claude-crown` | Use when starting any conversation - establishes how to find and use Claude Crown skills, requiring skill invo |

Invocation name is the **folder** name: `skills/taste-skill/` is invoked as `claude-crown:taste-skill`, whatever its frontmatter `name` says (measured 2026-09-13, Claude Code 2.1.270).
Add a row per skill you drop in. Source and license per vendored skill: see Credits.

## Layout

    .claude-plugin/plugin.json      manifest
    .claude-plugin/marketplace.json local marketplace, source "./"
    skills/                         one folder per skill
    agents/                         impeccable's four subagents
    hooks/                          SessionStart (Crown router, caveman) + UserPromptSubmit (caveman tracker) + PostToolUse/Stop (impeccable)
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
| `caveman`, `caveman-commit`, `caveman-review`, `compress` + SessionStart/UserPromptSubmit hooks | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | commit `92f892f` (installed 2026-04-09) | MIT, `skills/caveman/LICENSE` |
| 14 `superpowers` skills (`brainstorming` … `writing-skills`) | [obra/superpowers](https://github.com/obra/superpowers) via claude-plugins-official | 6.3.0 | MIT, `skills/using-superpowers/LICENSE` |
| 7 `ui-ux-pro-max` skills (`banner-design`, `brand`, `design`, `design-system`, `slides`, `ui-styling`, `ui-ux-pro-max`) | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | 2.6.2 | MIT, `skills/ui-ux-pro-max/LICENSE` |
| `claude-automation-recommender` | claude-code-setup, claude-plugins-official | 1.0.0 | `skills/claude-automation-recommender/LICENSE` |
| `codex-cli-runtime`, `codex-result-handling`, `gpt-5-4-prompting` — skills only, **no** runtime/hooks/commands/agent (they read the codex plugin's own manifest and `.generated/` types) | openai/codex plugin | 1.0.6 | `skills/codex-cli-runtime/LICENSE` + `NOTICE` |
| 14 Claude Desktop account skills (`docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`, `consolidate-memory`, `explain-usage`, `import-memory`, `morning`, `schedule`, `setup-claude`, `setup-cowork`; owner-authored `prompt-verstaendnis`, `security-review`) | Claude Desktop `skills-plugin` snapshot | 2026-09-13 | `LICENSE.txt` inside `docx`, `pdf`, `pptx`, `xlsx`, `skill-creator`; rest as shipped |
| `cowork-plugin-customizer`, `create-cowork-plugin` | Claude Desktop `cowork-plugin-management` | 0.2.2 | `skills/create-cowork-plugin/LICENSE` |

Private use only. Check upstream licenses before any redistribution.
