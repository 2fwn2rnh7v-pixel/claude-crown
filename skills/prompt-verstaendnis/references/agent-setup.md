# The three-agent setup — roles, handovers, adaptations

The user's standard working model: three roles that run in sequence with explicit handovers.
Whether they are three separate subagents, three phases of one session, or three named sections
of one answer depends on the runtime — the contract below stays the same.

---

## Roles

### Agent 1 — Research / analysis

- Inventory of what exists: modules touched, data model, current behaviour, existing tests,
  constraints from `CLAUDE.md` / the context router.
- External facts verified against primary documentation (fetch, do not recall) when a library
  or API is involved; dated.
- Threat and cost surface when relevant (hand-off to `security-review` and `api-guard`).
- Output: a short brief for Agent 2 — what is known, what is assumed, what is open. Assumptions
  are labelled as such.

### Agent 2 — Code / implementation

- Implements against the brief, inside the existing module boundaries, in the project's
  conventions (TypeScript, no `any`, English identifiers, German product copy).
- Small, reviewable steps; each step leaves the build green.
- Runs the accompanying modes of the review skills (Mode B) while writing: security notes and
  API notes at the end of each step, not a separate audit.
- Output: the change plus a note of what Agent 3 must cover — new paths, guards, edge cases.

### Agent 3 — Test / QA (Testsprite MCP)

- Writes and runs tests for every path Agent 2 named, plus negative tests for every guard.
- Uses the Testsprite MCP when it is connected; otherwise the project's test runner and browser
  tooling. Reports which one ran.
- Reproduces reported bugs before touching a fix; confirms the fix with the same test.
- Output: evidence — commands, results, counts. "Should work" is not a result.

## Handover protocol

```
Agent 1 → Agent 2
  brief: known facts / assumptions / open questions / files touched
Agent 2 → Agent 3
  change summary / new or changed paths / guards to test negatively / how to run
Agent 3 → user
  evidence: what ran, pass/fail counts, what is still untested and why
```

Each handover is written down (a short table or list), so the next role does not re-derive it.
A role that finds its input incomplete says so and asks for the missing piece instead of
guessing.

## Flexible adaptations

| Situation | Adaptation |
|---|---|
| The user addresses one agent only ("Agent 3 soll…") | Run that role only; do not invent the others |
| Task is research-only (concept, comparison) | Agent 1 produces the deliverable; Agents 2/3 are not spun up |
| Bug report | Agent 3 first (reproduce), then Agent 2 (fix), then Agent 3 (confirm) — order inverted |
| Very small change | One role does all three phases in sequence; still write the evidence |
| Parallel work | Split by file collision, not by role; assign file names in advance; the controller owns the seams |
| Subagent dies mid-task | Measure the state on disk first, then continue — never restart from zero blindly |

## Tool integration

- **Testsprite MCP** — Agent 3's default when available: generate and run tests, capture
  results. If the MCP is not connected, say so once and fall back to the project's runner.
- **Browser pane / Playwright** — for UI verification; screenshots are evidence.
- **Review skills** — `security-review` (auth, injection, access control) and `api-guard`
  (keys, limits, cost) run in Mode B alongside Agent 2 and in Mode A when the user asks for a
  review.
- **Verification before completion** — every role's "done" needs a fresh command output; the
  self-reflection block at the end refers back to the original prompt, layer by layer.

## Output shape when all three run

```
## Agent 1 — Research
<brief>

## Agent 2 — Code
<changes, steps, Mode B notes>

## Agent 3 — Test/QA
<evidence>

## Self-reflection (referring back to the prompt)
✅ / ⚠️ / ❌ per prompt aspect
**Overall assessment**: …
```
