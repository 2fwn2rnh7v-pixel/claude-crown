# Prompt patterns — decoded examples

The examples below reconstruct the user's prompt style from the patterns documented in
`SKILL.md` (typo table, five layers, quality markers, agent setup, self-reflection clause). The
German prompt text is the input data and stays German; the decoding is English. When a real
prompt arrives, decode it the same way and, if it shows a new pattern, add it here.

---

## Example 1 — full five-layer prompt

**Prompt (German, as typed):**

> Baue ein sehr detaliertes und spezifisches Konzept für das Team-Modul, wo man Mitarbeiter
> ein sein Team einladen kann und die Stunden direkt mit dem Stunden-Tracking verbunden sind.
> Agent 1 macht die Research zu den bestehenden Modulen, Agent 2 schreibt den Code, Agent 3
> testet mit Testsprite. Gib dir Mühe und arbeite organisiert. Hinterfrage am Ende mit
> Rücksoicht auf den gegebenen Prompt.

**Decoding:**

| Layer | Content |
|---|---|
| 1 Task | Concept + implementation for the team module: invite employees into a team, link hours to hours tracking |
| 2 Quality markers | "sehr detailliert", "spezifisch", "gib dir Mühe", "organisiert" — four markers → highest level, nothing abbreviated |
| 3 Agent setup | Explicit: Agent 1 research on existing modules, Agent 2 code, Agent 3 Testsprite tests |
| 4 Context | Agrarmonitor modules: team module, hours tracking (both known); implicit: customer database and orders may connect |
| 5 Self-reflection | Present ("Hinterfrage … mit Rücksoicht" → Rücksicht) — mandatory block at the end |

Typos corrected silently: "detaliertes" → detailliert, "ein sein Team" → in sein Team,
"Rücksoicht" → Rücksicht.

**Execution consequence:** research first (inventory of the team and hours modules, data model,
existing invitation flow), then a structured concept with headings per aspect (data model,
permissions, UI, edge cases), then code with the module boundaries respected, then Testsprite test
plan, then the self-reflection block with ✅ / ⚠️ / ❌ per prompt aspect.

## Example 2 — short prompt with agent reference

**Prompt:**

> Agent 3 soll nochmal über die Gutschriften drüber gehen, da ist was mit den Beträgen.

**Decoding:**

| Layer | Content |
|---|---|
| 1 Task | Re-test the credit-note system, suspected amount bug |
| 2 Quality markers | none explicit → normal depth, but "da ist was" = a real defect is suspected, so find it, do not guess |
| 3 Agent setup | Only Agent 3 (Test/QA) is addressed — do not spin up research or code agents unless the bug needs a fix |
| 4 Context | Credit-note system (known module); amounts → money handling, rounding, currency |
| 5 Self-reflection | Not written, still expected (standard) |

**Execution consequence:** reproduce with tests around amounts (rounding, negative values,
currency, totals), report the failing case precisely, propose the fix, hand to Agent 2 only if
the user wants it implemented. Close with the self-reflection.

## Example 3 — nested instructions in one sentence

**Prompt:**

> Mach die Karten-Ansicht so dass man die Aufträge sieht, aber nur die vom eigenen Team, und
> wenn man draufklickt soll die Kunden-Datenbank aufgehen, spezialiesiert auf mobile, und
> hinterfrage das ganze am Ende mit Rückbetracht auf den Prompt.

**Decoding — split the sentence into atomic instructions before anything else:**

1. Map view shows orders.
2. Filter: only the caller's own team (→ authorisation rule, not just a UI filter).
3. Click on an order opens the customer record (→ cross-module navigation map → customers).
4. "spezialiesiert auf mobile" → specialised for mobile: touch targets, viewport, performance.
5. Self-reflection clause present.

Layer 4 context: map view, orders, customer database, team module — four modules interact. The
user thinks in networks: check the permission model of the team module before building the
filter, otherwise the filter is cosmetic.

**Execution consequence:** treat point 2 as a security requirement (see the `security-review`
skill, category 3) and say so; build the UI after the data rule is settled.

## Example 4 — quality markers without an agent setup

**Prompt:**

> Erklär mir sehr spezifisch und strukturiert wie das Stunden-Tracking die Gutschriften
> beeinflusst.

**Decoding:** conceptual question, no build. Markers "sehr spezifisch", "strukturiert" →
structured explanation tied to Agrarmonitor's actual modules, not a generic essay. No agent setup
(step 3: "not relevant"). Self-reflection still at the end, short.

## Example 5 — marker stacking as an importance signal

**Prompt:**

> Sehr spezifisch detailliert und organisiert: Konzept für das komplette Rechte-System über alle
> Module.

**Decoding:** three markers stacked in the first words → this is an important task. Full
concept, every module covered individually (team, customers, orders, map, hours, credit notes),
permission matrix, migration path, open questions. Do not summarise where a table can list.

---

## Anti-patterns when decoding

| Wrong reaction | Right reaction |
|---|---|
| Asking "did you mean detailliert?" | Silently correct and proceed |
| Treating "Hinterfrage…" as a closing courtesy | Produce the structured self-reflection block |
| Answering the first sentence and dropping the nested ones | Split into atomic instructions, address each |
| Forcing three agents on a one-line question | Agent setup only when research + code + test are all in scope or the user names roles |
| Generic best-practice answer | Tie every point to the named modules |
| Summarising when "sehr detailliert" was asked | Work out every aspect individually |
