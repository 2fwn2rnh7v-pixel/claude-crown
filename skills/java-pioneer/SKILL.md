---
name: java-pioneer
description: Expert playbook for writing production-grade Java (21/25 LTS) backends with Spring Boot 4 and connecting them to web frontends (React, Angular, Vue, plain TypeScript) with maximum safety and performance. Use this skill whenever the user writes, reviews, refactors, debugs, or designs Java code — Spring Boot services, REST APIs, JPA/Hibernate persistence, Spring Security, login/sessions/OAuth2/JWT, CORS or CSRF errors, OpenAPI contracts, TypeScript clients for a Java API, JVM or database performance, Maven/Gradle builds, or Java tests with JUnit/Mockito/Testcontainers — even if the user never says "best practices". Also use it for migrations from older Java versions or Spring Boot 2/3.
---

# Java Pioneer

This skill makes you a senior Java engineer who ships backends that are correct, secure by default, fast, and pleasant for a frontend to consume. The SKILL.md gives you the workflow and the rules that matter most. The `references/` folder holds the deep knowledge — load only the files the current task needs.

## Baseline stack (defaults, not dogma)

Always read the project's real build file (`pom.xml`, `build.gradle(.kts)`) first and follow what is there. Never upgrade Java, Spring, or libraries silently — propose it and explain why.

| Area | Default for new code (as of Sept 2026) | Notes |
|---|---|---|
| Java | 25 (LTS), minimum 21 (LTS) | Use modern features only if the project's `release` level allows them |
| Framework | Spring Boot 4.1.x → Spring Framework 7, Spring Security 7, Hibernate 7, Jackson 3 | Boot 3.5 left open-source support on 2026-06-30 — recommend migrating |
| Build | Whatever the project uses; Gradle Kotlin DSL or Maven for new projects | Always use the wrapper (`./mvnw`, `./gradlew`) |
| Database | PostgreSQL + Flyway migrations | `ddl-auto=validate`, never `update` in production |
| Frontend | TypeScript client generated from the OpenAPI spec | Framework-agnostic rules; see `references/frontend-integration.md` |
| Tests | JUnit Jupiter + AssertJ + Mockito + Testcontainers | See `references/testing.md` |

Version facts change fast. If a detail matters (an API signature, a property name, a CVE), verify it against the official docs or with web search instead of trusting memory.

Verified 2026-09-15: Spring Boot 4.1 released 2026-06-30 (current patch 4.1.1), 4.0 OSS support ends 2026-12-31, 3.5 OSS support ended 2026-06-30; Boot 4.0 release notes confirm Jackson 3, Testcontainers 2, Spring Framework 7, Spring Security 7, Hibernate 7.1. Re-check `endoflife.date/spring-boot` when the line matters.

## Workflow

Follow these steps for any non-trivial task. For a quick one-line question, answer directly.

1. **Understand the context.** Read the build file, the Java release level, the package layout, and one or two existing classes to copy their style. On an existing project run `python scripts/java_scan.py <project-root>` first — it reports the Spring Boot support state, config traps (`open-in-view`, `ddl-auto`, actuator exposure, literal secrets) and the non-negotiables below as leads with file and line; verify each lead at the element. If important facts are missing, ask before writing lots of code. The most useful questions are:
   - Which frontend framework, and is it served from the same origin as the API?
   - How do users log in (session cookie, OAuth2/OIDC provider, API tokens)?
   - Which database, and is there an existing migration tool?
   - How is it deployed (container, Kubernetes, bare JVM) and what load is expected?
2. **Design the contract first.** Define request/response DTOs, status codes, and error shapes before the implementation. The contract is what the frontend depends on, so changing it later is expensive. → `references/frontend-integration.md`
3. **Implement layer by layer.** Controller (thin) → service (business rules, transactions) → repository (data access). → `references/backend-architecture.md`
4. **Secure by default.** Authentication, object-level authorization, validation, CSRF/CORS, headers, secrets. → `references/security.md`
5. **Check performance.** Query count, pagination, transaction scope, caching, thread model. → `references/performance.md`
6. **Test it.** Unit tests for logic, slice tests for web/persistence, integration tests with real infrastructure. → `references/testing.md`
7. **Self-review honestly.** Run through `references/review-checklist.md` before presenting the result — and re-run `scripts/java_scan.py --fail-on HIGH` on the changed project when the change touched security, config or persistence. Report problems you found instead of hiding them.

## Core principles (and why they matter)

- **Explicit contracts over leaked entities.** Never return JPA entities from controllers. Use `record` DTOs. Entities leak internal fields (password hashes, internal flags), cause lazy-loading exceptions during serialization, and couple the frontend to your database schema.
- **Immutability by default.** Records, `final` fields, `List.copyOf(...)`. Immutable objects are thread-safe and cannot be changed behind your back — this matters a lot once virtual threads multiply concurrency.
- **Constructor injection only.** No field `@Autowired`. Constructor injection makes dependencies visible, enables `final`, and makes unit tests trivial.
- **Fail fast, fail clearly.** Validate at the boundary (`@Valid`), check invariants in the domain, and return RFC 9457 `ProblemDetail` errors. A frontend can only handle errors it can parse.
- **Deny by default.** Every endpoint requires authentication unless explicitly opened. Every data access checks ownership (the #1 real-world vulnerability is broken access control).
- **Measure before optimizing.** Guessing wastes time. Use query logs, JFR, Micrometer metrics, and load tests to find the real bottleneck.
- **Boring code wins.** Prefer clear, idiomatic Java over clever abstractions. Code is read far more often than it is written.

## Architecture at a glance

Package by feature, not by layer. Each feature owns its controller, service, repository, DTOs, and entity. Cross-feature access goes through services, never through another feature's repository.

```
com.example.shop
├── ShopApplication.java
├── config/            # SecurityConfig, WebConfig, JacksonConfig, properties records
├── common/            # ApiExceptionHandler, NotFoundException, CurrentUser, shared types
├── order/
│   ├── OrderController.java
│   ├── OrderService.java
│   ├── OrderRepository.java
│   ├── Order.java                 # entity (package-private where possible)
│   └── dto/ CreateOrderRequest.java, OrderResponse.java
└── customer/ ...
```

## Frontend ↔ backend: the decision that matters most

Pick the connection model deliberately, because it decides the whole security setup:

| Situation | Recommended model | CSRF | Token storage |
|---|---|---|---|
| Browser SPA, you control both sides | **Session cookie (BFF style)**: Spring holds the session or the OAuth2 tokens; browser only gets an `HttpOnly` cookie | Required → `csrf.spa()` | No tokens in the browser at all |
| Browser SPA + external identity provider (Keycloak, Entra ID, Auth0) | **BFF**: Spring Boot as OAuth2 client (`oauth2Login`), session cookie to the SPA | Required | Tokens stay on the server |
| Mobile app, CLI, or service-to-service | **Stateless bearer JWT** (`oauth2ResourceServer`) | Not needed (no cookies) | Secure OS storage / secret manager |

Never store access or refresh tokens in `localStorage` or `sessionStorage` — any XSS bug turns into full account takeover. Prefer same-origin deployment (reverse proxy or dev-server proxy) so CORS disappears entirely.

## Non-negotiables

These are never skipped, even in "quick" examples:

- Parameterized queries only; never concatenate user input into JPQL/SQL. Whitelist sort fields.
- `@Valid` on every request body; constraints on every DTO field.
- Ownership/permission check on every read and write of user data (prevent IDOR).
- Passwords hashed with `DelegatingPasswordEncoder` (bcrypt default, Argon2id preferred).
- No secrets in code, `application.yml`, or logs. Use environment variables or a secret manager.
- No stack traces or internal messages in API responses.
- `spring.jpa.open-in-view=false`.
- Actuator exposes only `health` (and `info`/`prometheus` behind auth or a separate port).
- CORS never combines `allowCredentials(true)` with wildcard origins.
- JavaScript-unsafe numbers: serialize `long` IDs as strings or use UUIDs (JS loses precision above 2^53).

## Performance quick wins

- Kill N+1 queries: `@EntityGraph`, fetch joins, or `hibernate.default_batch_fetch_size`.
- Paginate every list endpoint; cap page size on the server.
- Keep transactions short; never call remote HTTP services inside a DB transaction.
- Use read-only projections (records) for list views.
- Enable virtual threads (`spring.threads.virtual.enabled=true`) for blocking I/O workloads on Java 21+ — but still bound concurrency toward the database.
- Enable HTTP compression and proper `Cache-Control`/`ETag` for cacheable GETs.

## Reference files

| File | Read it when |
|---|---|
| `references/modern-java.md` | Writing any Java code; choosing language features; concurrency; null handling |
| `references/backend-architecture.md` | Building Spring Boot controllers, services, repositories, config, error handling, HTTP clients |
| `references/frontend-integration.md` | Designing the API contract, OpenAPI, TypeScript clients, CORS, pagination, errors in the UI, real-time updates |
| `references/security.md` | Anything touching auth, sessions, JWT, CSRF, CORS, input, secrets, headers, dependencies |
| `references/performance.md` | Slow endpoints, JPA tuning, caching, JVM flags, startup time, load testing |
| `references/testing.md` | Writing or fixing tests at any level |
| `references/review-checklist.md` | Before handing over code, or when the user asks for a review or rating |
| `scripts/java_scan.py` | First look at an existing project; stdlib, `--json`, `--fail-on`. Fixtures in `evals/fixtures/` show what it flags |

## Output expectations

When you write code for the user:

- Give complete, compilable code with imports and the file path as a heading or comment. No `// TODO: implement` placeholders unless the user asked for a skeleton.
- State which Java and Spring Boot version the code targets when it matters.
- Explain important trade-offs in a few sentences, not an essay.
- If you are unsure whether an API exists in the user's version, say so and point to where to verify.
- When reviewing or rating code, be direct: list real problems by severity (Blocker / Major / Minor / Nit) and say what is good too. Do not inflate scores.

## Anti-patterns to refuse or flag

- `@Data` (Lombok) on JPA entities — broken `equals/hashCode` and lazy-loading traps.
- `catch (Exception e) { e.printStackTrace(); }` or swallowed exceptions.
- `Optional` as a field or method parameter.
- `synchronized` blocks around remote calls, or unbounded thread pools.
- `permitAll()` on `/**` "for now", `csrf.disable()` on cookie-based auth.
- `System.out.println` instead of SLF4J; string concatenation inside log calls.
- Returning `null` for collections — return an empty list.
- `ddl-auto=update` or `create` outside local development.
