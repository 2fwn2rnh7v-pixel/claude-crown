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

## Test

    bash hooks/test-session-start.sh

## Credits

`hooks/run-hook.cmd` and the shape of `hooks/session-start` come from
[obra/superpowers](https://github.com/obra/superpowers) (MIT).
