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
