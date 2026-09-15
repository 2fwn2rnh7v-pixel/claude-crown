# Security for Java Backends

## Table of contents
1. Threat model in one table (OWASP Top 10:2025)
2. Baseline SecurityFilterChain — browser SPA with session cookie
3. JSON login endpoint
4. BFF with an external identity provider (OAuth2/OIDC)
5. Stateless JWT resource server (mobile, service-to-service)
6. Passwords
7. Authorization and IDOR prevention
8. Input validation and injection
9. CSRF, cookies, sessions
10. Security headers
11. Secrets and configuration
12. Logging, errors, monitoring
13. Rate limiting and abuse
14. Supply chain
15. Other traps (SSRF, deserialization, uploads, actuator)

---

## 1. Threat model (OWASP Top 10:2025)

| Risk | What to do in a Spring app |
|---|---|
| A01 Broken Access Control | Deny by default; check ownership in every query; method security; test 403 cases |
| A02 Security Misconfiguration | No default passwords; actuator locked down; no stack traces; headers on; debug off |
| A03 Software Supply Chain Failures | Dependency scanning, lockfiles/verification, SBOM, pinned base images |
| A04 Cryptographic Failures | TLS everywhere; strong password hashing; no home-made crypto; secrets in a vault |
| A05 Injection | Parameterized queries; whitelisted sort/filter fields; output encoding in the frontend |
| A06 Insecure Design | Threat-model features (e.g., rate limits on login, idempotent payments) |
| A07 Authentication Failures | Session fixation protection; MFA for sensitive apps; lockout/throttling; secure reset flows |
| A08 Software or Data Integrity Failures | No Java deserialization of untrusted data; verify webhooks with signatures |
| A09 Security Logging and Alerting Failures | Log auth events and denials (without secrets); alert on anomalies |
| A10 Mishandling of Exceptional Conditions | Fail closed; generic error responses; no partial state on exceptions (transactions) |

---

## 2. Baseline SecurityFilterChain — browser SPA with session cookie

Targets Spring Security 7 (Spring Boot 4). Lambda DSL only.

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(HttpMethod.POST, "/api/auth/login").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/auth/me").permitAll()   // returns 401 body itself if anonymous
                .requestMatchers("/actuator/health/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/**").authenticated()
                .anyRequest().permitAll())            // static SPA assets; tighten if the API is the only content
            .csrf(csrf -> csrf.spa())                 // cookie XSRF-TOKEN + X-XSRF-TOKEN header, BREACH-safe
            .cors(Customizer.withDefaults())          // only matters if a CorsConfigurationSource bean exists
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint(new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED)))  // no redirect to login page for APIs
            .sessionManagement(session -> session
                .maximumSessions(5))
            .logout(logout -> logout
                .logoutUrl("/api/auth/logout")
                .logoutSuccessHandler(new HttpStatusReturningLogoutSuccessHandler(HttpStatus.NO_CONTENT))
                .deleteCookies("SESSION", "JSESSIONID"))
            .headers(headers -> headers
                .contentSecurityPolicy(csp -> csp.policyDirectives(
                    "default-src 'self'; script-src 'self'; object-src 'none'; " +
                    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"))
                .referrerPolicy(ref -> ref.policy(
                    ReferrerPolicyHeaderWriter.ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN))
                .permissionsPolicyHeader(pp -> pp.policy("camera=(), microphone=(), geolocation=()")));
        return http.build();
    }

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    @Bean
    AuthenticationManager authenticationManager(UserDetailsService users, PasswordEncoder encoder) {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider(users);
        provider.setPasswordEncoder(encoder);
        return new ProviderManager(provider);
    }
}
```
Session cookie settings:
```yaml
server:
  servlet:
    session:
      timeout: 30m
      cookie:
        http-only: true
        secure: true
        same-site: lax
```
Verify method names against your Spring Security version (e.g., `permissionsPolicyHeader`, the `DaoAuthenticationProvider` constructor) — they have changed between 6.x and 7.x. For horizontal scaling, store sessions in Redis or JDBC with Spring Session.

---

## 3. JSON login endpoint

Since Spring Security 6, a manual login must save the security context explicitly.

```java
@RestController
@RequestMapping("/api/auth")
class AuthController {

    private final AuthenticationManager authenticationManager;
    private final SecurityContextRepository contextRepository = new HttpSessionSecurityContextRepository();
    private final SecurityContextHolderStrategy holderStrategy = SecurityContextHolder.getContextHolderStrategy();

    AuthController(AuthenticationManager authenticationManager) {
        this.authenticationManager = authenticationManager;
    }

    record LoginRequest(@NotBlank @Size(max = 254) String username,
                        @NotBlank @Size(max = 128) String password) {}

    record MeResponse(String username, List<String> roles) {}

    @PostMapping("/login")
    ResponseEntity<Void> login(@Valid @RequestBody LoginRequest body,
                               HttpServletRequest request, HttpServletResponse response) {
        Authentication authentication = authenticationManager.authenticate(
                UsernamePasswordAuthenticationToken.unauthenticated(body.username(), body.password()));

        if (request.getSession(false) != null) {
            request.changeSessionId();                 // session fixation protection
        }
        SecurityContext context = holderStrategy.createEmptyContext();
        context.setAuthentication(authentication);
        holderStrategy.setContext(context);
        contextRepository.saveContext(context, request, response);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/me")
    ResponseEntity<MeResponse> me(Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()
                || authentication instanceof AnonymousAuthenticationToken) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        List<String> roles = authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority).toList();
        return ResponseEntity.ok(new MeResponse(authentication.getName(), roles));
    }
}
```
- The login POST is CSRF-protected too (login CSRF is a real attack). The SPA must call `GET /api/auth/me` first so the `XSRF-TOKEN` cookie exists, then send it as `X-XSRF-TOKEN`.
- `BadCredentialsException` must lead to a generic 401 ("Invalid username or password") — never reveal whether the username exists.
- Throttle login attempts (section 13).
- Also consider Spring Security's built-in `formLogin` with custom success/failure handlers returning status codes; it handles session fixation and CSRF token rotation automatically.

---

## 4. BFF with an external identity provider

```java
http
    .oauth2Login(oauth -> oauth
        .successHandler(new SimpleUrlAuthenticationSuccessHandler("/")))
    .oauth2Client(Customizer.withDefaults())
    .csrf(csrf -> csrf.spa())
    .exceptionHandling(ex -> ex
        .defaultAuthenticationEntryPointFor(
            new HttpStatusEntryPoint(HttpStatus.UNAUTHORIZED),
            PathPatternRequestMatcher.withDefaults().matcher("/api/**")));
```
```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          keycloak:
            client-id: shop-bff
            client-secret: ${OIDC_CLIENT_SECRET}
            scope: openid,profile,email
        provider:
          keycloak:
            issuer-uri: https://id.example.com/realms/shop
```
- Tokens live in the server-side session; the browser only has the session cookie.
- Calls from the BFF to downstream APIs use `OAuth2AuthorizedClientManager` to attach and refresh tokens.
- Use OIDC back-channel/RP-initiated logout so logging out ends the IdP session too.

---

## 5. Stateless JWT resource server

For APIs consumed by mobile apps or other services — not by your browser SPA directly.
```java
@Bean
SecurityFilterChain apiChain(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
        .oauth2ResourceServer(rs -> rs.jwt(Customizer.withDefaults()))
        .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .csrf(csrf -> csrf.disable());   // acceptable ONLY because no cookies authenticate requests
    return http.build();
}
```
```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://id.example.com/realms/shop
          audiences: shop-api
```
- Validate issuer, audience, expiry, and signature (asymmetric keys via JWKS; never accept `alg: none`).
- Short access-token lifetime (5–15 min). Don't build your own token issuer — use Spring Authorization Server or an IdP.
- Map roles from claims with a `JwtAuthenticationConverter`.
- JWTs cannot be revoked instantly; that's why browser apps are better off with sessions.

---

## 6. Passwords

- `PasswordEncoderFactories.createDelegatingPasswordEncoder()` — bcrypt by default, stores the algorithm prefix (`{bcrypt}`) so you can upgrade later.
- Argon2id is the modern recommendation (`Argon2PasswordEncoder`, needs BouncyCastle). Tune for roughly 0.5–1 s on your hardware at login.
- Implement `UserDetailsPasswordService` to re-hash transparently on login when parameters change.
- Enforce minimum length (≥ 12 is a good default), allow long passphrases, check against breached-password lists; don't force arbitrary composition rules.
- Password reset: single-use, short-lived, random tokens (`SecureRandom`, ≥ 128 bits), stored hashed; same response whether the email exists or not.
- Offer MFA (TOTP/WebAuthn passkeys) for sensitive applications — Spring Security has passkey (WebAuthn) support.

---

## 7. Authorization and IDOR prevention

Authentication says *who*; authorization says *what* — the most common real vulnerability is missing object-level checks.

```java
// Good: ownership is part of the query
orders.findByIdAndOwnerId(id, currentUser.id())

// Good: method security with a bean check
@PreAuthorize("hasRole('ADMIN') or @orderAccess.canRead(#id, authentication)")
public OrderResponse find(UUID id) { ... }
```
- Never trust IDs, roles, prices, or owner fields from the request body.
- Return 404 (not 403) for objects the user may not see, so existence isn't leaked.
- Use random UUIDs for public identifiers; sequential IDs make enumeration easy (but UUIDs are **not** a substitute for access checks).
- Write tests: "user B cannot read/update/delete user A's order".

---

## 8. Input validation and injection

- Bean Validation on every DTO; bound every string and list size.
- Validate business rules in the service (e.g., quantity ≤ stock).
- **SQL/JPQL:** named parameters only.
```java
// NEVER
em.createQuery("select u from User u where u.email = '" + email + "'");
// ALWAYS
em.createQuery("select u from User u where u.email = :email", User.class).setParameter("email", email);
```
- Dynamic sorting: map user input through a whitelist.
```java
private static final Map<String, String> SORTABLE = Map.of("created", "createdAt", "total", "total");

Sort toSort(String field, String dir) {
    String property = SORTABLE.get(field);
    if (property == null) throw new BadRequestException("Unsupported sort field");
    return Sort.by("desc".equalsIgnoreCase(dir) ? Sort.Direction.DESC : Sort.Direction.ASC, property);
}
```
- Native queries: same rules. With `JdbcClient`, use `.param(...)`.
- **XSS:** the backend returns JSON with `Content-Type: application/json`; the frontend renders with text binding. Never use `innerHTML`/`dangerouslySetInnerHTML`/`[innerHTML]` with user data unless sanitized (DOMPurify). CSP is the second line of defense.
- **Log injection:** don't log raw user input with line breaks; structured JSON logging neutralizes this.
- **Command injection:** avoid `Runtime.exec`; if unavoidable, use `ProcessBuilder` with an argument list and a whitelist.
- **Path traversal:** normalize and verify `resolved.startsWith(baseDir)`; better, never build paths from user input.
- **XXE:** if parsing XML, disable DTDs and external entities.
- **Regex DoS:** avoid catastrophic backtracking patterns on user input; bound input length first.

---

## 9. CSRF, cookies, sessions

- Any authentication carried by cookies needs CSRF protection. `csrf.spa()` sets up the cookie-to-header pattern with BREACH-safe token handling.
- `SameSite=Lax` is a strong extra layer, not a replacement.
- GET requests must never change state (CSRF protection doesn't cover them).
- Cookie flags: `HttpOnly` (session), `Secure`, `SameSite`, narrow `Path`. Consider the `__Host-` name prefix for session cookies when on a single host.
- Session fixation: change the session ID on login (automatic with `formLogin`/`oauth2Login`, manual in custom endpoints — see section 3).
- Idle timeout plus an absolute lifetime for sensitive apps; invalidate sessions on password change.

---

## 10. Security headers

Spring Security sets sensible defaults (`X-Content-Type-Options`, `X-Frame-Options: DENY`, cache control, HSTS on HTTPS). Add:
- **Content-Security-Policy** tuned to the frontend (no `unsafe-inline` scripts; use nonces/hashes if needed).
- **Referrer-Policy:** `strict-origin-when-cross-origin`.
- **Permissions-Policy:** disable unused browser features.
- **HSTS** with `includeSubDomains` once all subdomains are HTTPS.

If a reverse proxy serves the frontend, set the headers there for static files too. Check with securityheaders.com or Mozilla Observatory.

---

## 11. Secrets and configuration

- Secrets from environment variables, Kubernetes secrets, or a vault (Spring Cloud Vault, cloud secret managers). Never in Git, never in `application.yml` defaults, never in Docker images.
- Scan the repository for secrets (gitleaks, GitHub secret scanning).
- Rotate credentials; use short-lived database credentials where possible.
- Use `SecureRandom` for anything security-relevant; never `Random` or `Math.random()`.
- TLS for every external connection, including the database (`sslmode=verify-full` for PostgreSQL).
- Least privilege DB user: the application user can't `DROP` tables; migrations may use a separate user.

---

## 12. Logging, errors, monitoring

- Log: successful/failed logins, logouts, access denials, password changes, privilege changes, admin actions — with user ID, IP, and trace ID.
- Never log: passwords, tokens, session IDs, full card numbers, secrets, or unnecessary personal data (GDPR).
- `server.error.include-stacktrace=never`, `include-message=never`; use `ProblemDetail` with a reference ID.
- Alert on bursts of 401/403, unusual 500 rates, and login failures.

---

## 13. Rate limiting and abuse

- Throttle login, password reset, registration, and expensive endpoints per IP and per account.
- Implement at the gateway/reverse proxy, or in the app with Bucket4j (backed by Redis when running multiple instances).
- Return 429 with `Retry-After`.
- Add CAPTCHA or proof-of-work only after repeated failures, to keep UX good.
- Set request size limits (`server.tomcat.max-swallow-size`, multipart limits, Bean Validation sizes).

---

## 14. Supply chain

- Scan dependencies continuously: OWASP Dependency-Check, Dependabot/Renovate, Snyk, or GitHub Advanced Security.
- Generate an SBOM (CycloneDX plugin; Spring Boot can expose it via the `sbom` actuator endpoint).
- Use the Spring Boot BOM for consistent versions; avoid overriding managed versions without reason.
- Enable Gradle dependency verification or Maven checksum policies; use the build wrapper with a checksum.
- Minimal, regularly rebuilt container images (distroless or slim JRE), run as non-root.
- Stay on a supported Spring Boot line — unsupported lines stop receiving CVE fixes.

---

## 15. Other traps

- **SSRF:** when fetching user-provided URLs, allowlist hosts, block private/link-local IP ranges after DNS resolution, disable redirects, and set timeouts.
- **Deserialization:** never use Java native serialization for untrusted input; never enable Jackson polymorphic default typing; use explicit `@JsonTypeInfo` with a whitelist if polymorphism is needed.
- **Mass assignment:** request DTOs contain only client-writable fields.
- **Actuator:** expose only `health` publicly; `env`, `heapdump`, `configprops`, `loggers` leak secrets or allow tampering — keep them off or behind admin auth on an internal port.
- **Webhooks:** verify HMAC signatures with constant-time comparison (`MessageDigest.isEqual`), check timestamps to prevent replay.
- **Timing attacks:** compare secrets with `MessageDigest.isEqual`, not `equals`.
- **H2 console / Swagger UI / DevTools:** never enabled in production.
