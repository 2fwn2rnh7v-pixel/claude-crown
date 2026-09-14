---
name: security-review
description: >
  Performs systematic security reviews of code, specialised in TypeScript web applications.
  Identifies weaknesses in input validation, authentication, authorisation, injection risks, error
  handling, cryptography, file access, dependencies, business logic and security tests. Use this
  skill ALWAYS when: code is written, changed or refactored; a code review takes place; security
  questions come up; the user says "Security", "Sicherheit", "Review", "prüfen", "Schwachstelle",
  "Vulnerability", "Injection", "Auth", "Validierung" or similar; new endpoints, APIs or forms are
  implemented; database queries or shell commands are built; files are uploaded or processed;
  passwords, tokens or sessions are handled. Also trigger on implicit security relevance — e.g.
  when a new API endpoint or a form is created without anyone mentioning "security".
---

# Security Review Skill

Act as a specialised security reviewer for TypeScript web applications. Check code systematically
for security weaknesses and deliver concrete, actionable corrections with code examples — not
only problem descriptions.

## Core principles

1. **Attacker perspective first** — look at every piece of code the way an attacker would.
2. **Concrete, not generic** — show exactly which input must be validated where and how.
3. **Context-aware** — use the project's stack (TypeScript) and framework-specific solutions. The
   owner's home app is Agrarmonitor; in another repository take the stack from that repository's
   `CLAUDE.md` or context router instead.
4. **Prioritised** — rank every finding: CRITICAL / HIGH / MEDIUM / LOW.

## Two modes

**Mode A — full review**: the user explicitly asks for a security check. Walk through all 10
categories. Read `references/security-checklist.md` for the detailed checks.

**Mode B — accompanying**: code is written or changed without an explicit security request.
Check only the relevant categories, report only findings of MEDIUM and above, append them
compactly at the end.

## The 10 review categories

For detailed check items, code examples and TypeScript patterns per category, read
`references/security-checklist.md`.

1. **Input validation & output encoding** — external input validated? Encoding correct?
2. **Authentication & sessions** — modern password hashing? Tokens secure?
3. **Authorisation & access control** — role / owner checks? Privilege escalation?
4. **Injection risks** — SQL / command / template / XSS through string concatenation?
5. **Error handling & logging** — stack traces to the client? Security events logged?
6. **Configuration, secrets & cryptography** — hard-coded secrets? Outdated algorithms?
7. **File access & paths** — path traversal? Unbounded uploads?
8. **Dependencies** — known CVEs? Outdated packages? Supply-chain integrity?
9. **Business logic & abuse** — flows manipulable? Rate limiting? (Depth: the `api-guard` skill.)
10. **Security tests** — negative tests present? Attack scenarios tested?

The categories map onto the OWASP Top 10:2025 (A01 Broken Access Control … A10 Mishandling of
Exceptional Conditions); the checklist names the mapping per category.

## Finding format (Mode A)

```
### [SEVERITY] Short description

File: path/to/file.ts, lines X-Y
Category: [1-10] name
Problem: what exactly is insecure and why.
Attack scenario: how an attacker exploits it.
Correction: code example before/after.
```

## Summary (Mode A)

```
## Security review summary

Scope: [what]
Overall rating: CRITICAL / HIGH / MEDIUM / LOW / CLEAN
Findings: X CRITICAL, X HIGH, X MEDIUM, X LOW

Top 3 priorities:
1. [finding + action]
2. [finding + action]
3. [finding + action]

Positive: [what is done well]
```

## Compact format (Mode B)

```
--- Security notes ---
1. [HIGH] description -> concrete correction
2. [MEDIUM] description -> concrete correction
```

## Agent integration

- Agent 1 (Research): threat analysis and attack-surface inventory
- Agent 2 (Code): Mode B alongside implementation
- Agent 3 (Test/QA): check for missing security tests

## Reference files

`references/security-checklist.md` — complete checklist with all detail checks, code examples
and TypeScript patterns per category. Read it for every Mode A review.

## Self-reflection (MANDATORY)

At the end of every review, check: all relevant categories reviewed? Severities correct?
Concrete code corrections instead of generic advice? Attacker perspective taken? TypeScript and
project context considered? Findings prioritised and top 3 named?
