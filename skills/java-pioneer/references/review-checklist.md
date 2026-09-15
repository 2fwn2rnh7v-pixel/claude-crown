# Review Checklist and Honest Rating

Use this before handing over code, and whenever the user asks for a review or a rating. Be direct: a review that hides problems is worthless.

## Severity levels

| Level | Meaning | Examples |
|---|---|---|
| **Blocker** | Security hole, data loss, or wrong behavior. Must fix before merge. | SQL injection, missing ownership check, secrets in code, lost updates |
| **Major** | Will cause real problems in production or maintenance. | N+1 queries on a list endpoint, no pagination, no timeouts, entity returned from controller |
| **Minor** | Worth fixing, low risk. | Missing test for an edge case, unclear naming, duplicated mapping code |
| **Nit** | Style/preference. Never block on these. | Formatting, import order |

## Rating scale (when asked to rate)

Give a score out of 10 and justify it with the findings. Don't round up to be nice.

- **9–10:** Production-ready. Secure, tested, clear. Only nits.
- **7–8:** Solid. A few minors or one easily fixed major.
- **5–6:** Works, but several majors. Needs another iteration.
- **3–4:** Significant design or security problems.
- **1–2:** Unsafe or fundamentally broken.

Any open **Blocker** caps the score at 4.

Report format:
```
Score: X/10
Blockers: ...
Majors: ...
Minors: ...
Nits: ...
What's good: ...
Next steps (in priority order): ...
```

## Checklist

### Correctness
- [ ] Compiles against the project's Java and Spring Boot versions; no preview features unless agreed
- [ ] Null handling is explicit; no `Optional.get()` without a check
- [ ] Money uses `BigDecimal`; time uses `java.time` with `Instant` for timestamps
- [ ] Transactions wrap all writes that must succeed together
- [ ] Concurrent updates are handled (`@Version`, `If-Match`)
- [ ] Exceptions are neither swallowed nor leaked to clients

### Security
- [ ] Every endpoint is authenticated unless intentionally public
- [ ] Every data access checks ownership/permissions (test for user B vs. user A exists)
- [ ] All request DTOs are validated with bounded sizes; no mass-assignment fields
- [ ] Queries are parameterized; sort/filter fields are whitelisted
- [ ] CSRF enabled for cookie auth; CORS lists exact origins
- [ ] No tokens in `localStorage`; cookies are `HttpOnly`, `Secure`, `SameSite`
- [ ] No secrets, passwords, or tokens in code, config defaults, or logs
- [ ] Error responses are `ProblemDetail` without internal details
- [ ] Actuator/Swagger/H2 console are not publicly exposed
- [ ] New dependencies are necessary, maintained, and free of known CVEs

### Performance
- [ ] No N+1 queries (checked with SQL log or statistics)
- [ ] Lists are paginated with a server-side maximum
- [ ] Indexes exist for new query patterns (migration included)
- [ ] No remote calls inside transactions; all outbound calls have timeouts
- [ ] Caches are bounded, expiring, and keyed correctly per user where needed
- [ ] `open-in-view` is disabled

### API contract and frontend
- [ ] DTOs (records), never entities, cross the HTTP boundary
- [ ] Status codes match the conventions; `201` includes `Location`
- [ ] `long` IDs are strings in JSON (or UUIDs are used)
- [ ] OpenAPI spec reflects the change; generated TypeScript types updated
- [ ] Breaking changes are avoided or versioned

### Design and readability
- [ ] Package by feature; controllers thin; business logic in services/domain
- [ ] Constructor injection; `final` fields; immutable DTOs
- [ ] Names describe intent; methods are short and focused
- [ ] No dead code, commented-out code, or unexplained TODOs
- [ ] Logging uses SLF4J placeholders at sensible levels

### Tests
- [ ] Unit tests for business rules, including failure paths
- [ ] Web slice tests for validation, status codes, and security (401/403/CSRF)
- [ ] Integration tests use Testcontainers, not H2
- [ ] Tests are deterministic (fixed `Clock`, no `sleep`)
- [ ] A bug fix includes a test that reproduced the bug
