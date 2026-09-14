---
name: prompt-verstaendnis
description: >
  Interprets and understands the prompts of a German-speaking developer working on his own app
  (Agrarmonitor, TypeScript). The user writes fast, directly and with natural typos — this skill
  decodes the actual intent, recognises the recurring three-agent setup (Research → Code → Test),
  identifies quality requirements and makes sure the self-reflection clause at the end of every
  piece of work is honoured. Use this skill ALWAYS when: the user writes a complex development
  prompt in German; mentions an agent setup; uses terms like "sehr detailliert", "spezifisch",
  "hinterfrage", "Agenten", "Testsprite", "Agrarmonitor"; or when the prompt contains several
  nested instructions that must be untangled. Also trigger on short prompts when they contain
  agent references or quality markers.
---

# Prompt Understanding Skill

This skill enables precise understanding and execution of prompts from one specific user. The
user develops Agrarmonitor (a TypeScript app) and communicates in a characteristic style that is
easy to misread without this skill. In another repository the same decoding applies; only the
context in step 4 changes — take it from that repository's `CLAUDE.md` or context router.

## Why this skill exists

The user thinks fast and types in flow. His prompts are densely packed with information, contain
typos, and assume that Claude already knows the Agrarmonitor context, the agent setup and the
implicit quality expectations. Without structured decoding, partial instructions get lost or are
prioritised wrongly.

---

## Step 1: Prompt decoding

On every incoming prompt run this analysis sequence — **internally, not as output to the user**:

### 1.1 Typo correction (silent, never mentioned)

The user makes consistent typos. Never comment on them; interpret them correctly and silently:

| Common spelling             | Intended meaning                     |
|-----------------------------|--------------------------------------|
| detaliert / detaliert       | detailliert (detailed)               |
| ausarbietung                | Ausarbeitung (elaboration)           |
| ein sein Team               | in sein Team (into his team)         |
| spezialiesiert              | spezialisiert (specialised)          |
| rücksoicht / rückbetracht   | Rücksicht / Rückbezug (with regard to / referring back) |
| etablieren (in context)     | einbinden / integrieren (integrate)  |
| Testsprite                  | Testsprite MCP (testing tool)        |

Ground rule: if a word phonetically or visually resembles a German word, that word is meant.
Never ask whether something is a typo — interpret correctly and execute.

### 1.2 Structure extraction

Every prompt from the user follows a recurring pattern with up to 5 layers. Extract these layers
in exactly this order:

```
┌─────────────────────────────────────────────────┐
│ LAYER 1: TASK                                   │
│ What concretely is to be done?                  │
│ → first sentence(s) of the prompt               │
├─────────────────────────────────────────────────┤
│ LAYER 2: QUALITY MARKERS                        │
│ How deep / precise should the work be?          │
│ → signal words: "sehr", "spezifisch",           │
│   "detailliert", "gib dir Mühe", "organisiert"  │
├─────────────────────────────────────────────────┤
│ LAYER 3: AGENT SETUP                            │
│ Which agent roles are assigned?                 │
│ → see reference: references/agent-setup.md      │
├─────────────────────────────────────────────────┤
│ LAYER 4: CONTEXT REFERENCES                     │
│ Are Agrarmonitor, modules or tools referenced?  │
│ → keep known modules & tech stack in mind       │
├─────────────────────────────────────────────────┤
│ LAYER 5: SELF-REFLECTION CLAUSE                 │
│ Almost always at the end: "Hinterfrage..."      │
│ → MANDATORY: always run it, even if omitted     │
└─────────────────────────────────────────────────┘
```

For a detailed pattern analysis with real examples, read `references/prompt-patterns.md`.

---

## Step 2: Interpreting quality markers

The user uses intensity signals that directly change the expected output depth. These are not
filler — the user means every word:

| Signal in the prompt             | Expected reaction                                               |
|----------------------------------|-----------------------------------------------------------------|
| "sehr detailliert"               | Work out every aspect individually, no summaries                |
| "sehr spezifisch"                | No generic answers, always tied to Agrarmonitor                 |
| "organisiert"                    | Clear structure with headings, sections, order                  |
| "spezialisiert"                  | Technically deep, not superficial                               |
| "gib dir Mühe"                   | Maximum quality, no shortcuts, no "good enough"                 |
| "strukturiert"                   | Logical build-up, traceable steps                               |
| Several markers combined         | Highest quality level — extensive AND precise                   |

When the user combines 3+ markers in one prompt (e.g. "sehr spezifisch detailliert und
organisiert"), it means: this is an important task. Invest maximum care. Abbreviate nothing.

---

## Step 3: Recognising and applying the agent setup

The user works with a **three-agent system**. The base structure is:

| Agent   | Core role                       | Standard task                                       |
|---------|---------------------------------|-----------------------------------------------------|
| Agent 1 | **Research / analysis**         | Gather information, verify, build context           |
| Agent 2 | **Code / implementation**       | Write code, implement architecture                  |
| Agent 3 | **Test / QA (Testsprite MCP)**  | Hunt errors, test, ensure quality                   |

For the complete agent configuration with role descriptions, handover protocols and flexible
adaptations, read `references/agent-setup.md`.

### When to apply the agent setup

- **Named explicitly**: the user writes "Dreier-Agenten-Setup", "3 Agenten", or describes roles →
  apply the setup in a structured way immediately.
- **Recognisable implicitly**: the user describes a task that spans research, coding AND
  testing → propose and apply the agent setup.
- **Not relevant**: simple questions, short changes, conceptual discussions → do not force an
  agent setup.

---

## Step 4: Agrarmonitor context

Agrarmonitor is the user's app. Always keep these assumptions in the background:

- **Tech stack**: TypeScript (main language)
- **Known modules** (extracted from prompts): team module, customer database, orders, map view,
  hours tracking, credit-note system
- **Architecture assumption**: modular build, different areas / modules that interact
- **User role**: the user is developer AND product owner — he thinks in features (what it
  should do) and implementation (how it should be built) at the same time

When the user describes a new module or feature, always check whether it interacts with known
modules. The user thinks in networks — single features never stand isolated.

In another repository, replace this block with that project's stack and module map (in this
workspace: `Company/Context/Context.md` is the router; Phoenix = Next.js 16 + Supabase + Java
API, landing page = TanStack Start on Cloudflare Workers).

---

## Step 5: Self-reflection (MANDATORY)

The user ends almost every prompt with a variant of:
- "Hinterfrage am Ende mit Rücksicht auf den gegebenen Prompt"
- "Hinterfrage deine Ausarbeitung mit Rückbetracht auf den Prompt"
- "Hinterfrage mit Rücksicht auf den Prompt"

### What is meant

This is NOT an optional politeness formula. The user expects a **structured self-check** at
the end of every piece of work. It covers:

1. **Completeness check**: was every aspect of the prompt addressed? Go through it point by point.
2. **Prompt-fidelity check**: does the work match what was actually asked — or did it drift?
3. **Quality check**: were the quality markers honoured? Is it really "sehr detailliert" when
   that was demanded?
4. **Agent check**: were the agent roles assigned and executed correctly?
5. **Gap identification**: what is still missing? What could be improved?

Format of the self-reflection:
```
## Self-reflection (referring back to the prompt)

✅ [aspect fulfilled] — [short reasoning]
✅ [another fulfilled aspect]
⚠️ [aspect partially fulfilled] — [what is missing]
❌ [aspect not fulfilled] — [why & next steps]

**Overall assessment**: [whether the prompt was answered completely]
```

Run the self-reflection even when the user does not mention it explicitly in a given prompt —
it is his standard expectation.

---

## Summary: processing pipeline

Run this pipeline on every incoming prompt:

```
PROMPT IN
     │
     ▼
[1] silently correct typos
     │
     ▼
[2] extract the 5-layer structure
     │
     ▼
[3] quality markers → determine depth
     │
     ▼
[4] recognise & configure the agent setup
     │
     ▼
[5] bring in the Agrarmonitor (or repository) context
     │
     ▼
[6] EXECUTION at full depth
     │
     ▼
[7] self-reflection against the original prompt
     │
     ▼
OUTPUT TO USER
```

---

## Reference files

- `references/prompt-patterns.md` — detailed analysis of real prompt examples with decoding of
  every layer. Read it when unsure how to interpret a new prompt.
- `references/agent-setup.md` — complete description of the three-agent system with roles,
  handover protocols, flexible adaptations and tool integration (Testsprite MCP). Read it for
  every task that requires an agent setup.
