# Frontend ↔ Java Backend Integration

## Table of contents
1. Deployment topology: same-origin first
2. API design conventions
3. OpenAPI and generated TypeScript clients
4. Authentication from the browser
5. Error handling in the frontend
6. Pagination, filtering, sorting
7. Data types across the wire
8. Concurrency, idempotency, caching
9. CORS (when you cannot avoid it)
10. Real-time updates
11. File upload and download
12. API versioning

---

## 1. Deployment topology: same-origin first

The simplest secure setup is **one origin** for UI and API:

- Production: a reverse proxy (nginx, Traefik, cloud load balancer) routes `/api/**` to Spring Boot and everything else to the static frontend. Or Spring Boot serves the built frontend from `src/main/resources/static`.
- Development: the frontend dev server proxies API calls, so the browser never sees another origin.

```ts
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://localhost:8080",
    },
  },
});
```
Same-origin means: no CORS configuration, cookies with `SameSite=Lax` work, and CSRF protection is straightforward. Angular (`proxy.conf.json`) and other dev servers have the same feature.

When serving an SPA from Spring Boot, forward unknown non-API paths to `index.html` so client-side routing works, but never for `/api/**` (API 404s must stay 404s).

---

## 2. API design conventions

- Resource nouns, plural: `/api/v1/orders`, `/api/v1/orders/{id}/lines`.
- Methods: `GET` read (safe), `POST` create or non-idempotent action, `PUT` full replace (idempotent), `PATCH` partial update, `DELETE` remove (idempotent).
- Status codes:

| Code | Use |
|---|---|
| 200 | Success with body |
| 201 | Created — include `Location` header |
| 204 | Success, no body |
| 400 | Malformed request / validation failed |
| 401 | Not authenticated |
| 403 | Authenticated but not allowed |
| 404 | Not found **or** not visible to this user (don't reveal existence) |
| 409 | Conflict (version mismatch, duplicate) |
| 412 | `If-Match` precondition failed |
| 422 | Semantically invalid business request (optional; many teams use 400) |
| 429 | Rate limited — include `Retry-After` |
| 500 | Unexpected — generic message plus reference ID |

- JSON field names in `camelCase`, consistent across the API.
- Actions that don't map to CRUD: `POST /api/v1/orders/{id}/cancel`.
- Keep responses shaped for the UI's needs, but don't build one endpoint per component. If screens need very different shapes, consider a BFF layer or GraphQL (Spring for GraphQL).

---

## 3. OpenAPI and generated TypeScript clients

Hand-written frontend types drift from the backend. Generate them.

**Backend (code-first):** add springdoc-openapi (use the major line that matches your Spring Boot version — check its compatibility table). The spec is served at `/v3/api-docs`. Disable Swagger UI in production or protect it:
```yaml
springdoc:
  swagger-ui:
    enabled: false        # enable only in the local profile
```
Annotate where the generated spec is ambiguous (`@Schema`, `@Operation`, `@ApiResponse`).

**Export the spec in the build** (e.g., springdoc's Maven/Gradle plugin) and commit it or publish it as a build artifact, so the frontend can generate types without a running backend. A CI check that fails on unintended spec changes catches breaking changes early.

**Frontend:** generate types with `openapi-typescript` and call the API with the type-safe `openapi-fetch` client (or use OpenAPI Generator / orval if the team prefers generated services and React Query hooks).

```bash
npx openapi-typescript ./openapi.json -o ./src/api/schema.d.ts
```

```ts
// src/api/client.ts
import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

function readCookie(name: string): string | undefined {
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : undefined;
}

const csrfMiddleware: Middleware = {
  onRequest({ request }) {
    if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
      const token = readCookie("XSRF-TOKEN");
      if (token) request.headers.set("X-XSRF-TOKEN", token);
    }
    return request;
  },
};

export const api = createClient<paths>({ baseUrl: "/", credentials: "same-origin" });
api.use(csrfMiddleware);
```

```ts
// usage — path, params, and response are fully typed
const { data, error } = await api.GET("/api/v1/orders/{id}", {
  params: { path: { id: orderId } },
});
if (error) handleProblem(error);
```

Contract-first (write the OpenAPI file, generate Spring interfaces with OpenAPI Generator) is also valid and better when several teams consume the API. Pick one approach per project.

---

## 4. Authentication from the browser

Recommended (see `security.md` for the server side):

1. SPA calls `GET /api/auth/me` on startup → 200 with the user, or 401.
2. Login form posts JSON to `POST /api/auth/login` → server creates the session and sets an `HttpOnly; Secure; SameSite=Lax` cookie.
3. After login and logout, call `GET /api/auth/me` again so the server issues a fresh `XSRF-TOKEN` cookie.
4. All state-changing requests send `X-XSRF-TOKEN` (middleware above).
5. A global response handler redirects to the login screen on 401 and shows "not allowed" on 403.

With an external identity provider, the SPA navigates the **whole page** to `/oauth2/authorization/{provider}`; Spring Boot handles the code flow (with PKCE) and keeps tokens server-side (BFF). The SPA never touches tokens.

Rules:
- Never store tokens in `localStorage`/`sessionStorage`.
- Frontend authorization (hiding buttons) is UX only. The backend must enforce every rule.
- Handle session expiry gracefully: on 401 during an action, keep form state and re-authenticate.

---

## 5. Error handling in the frontend

The backend returns `application/problem+json`:
```json
{
  "type": "about:blank",
  "title": "Validation failed",
  "status": 400,
  "detail": "Invalid request content.",
  "instance": "/api/v1/orders",
  "errors": [{ "field": "lines[0].quantity", "message": "must be greater than 0" }]
}
```

```ts
export interface ProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: { field: string; message: string }[];
}

export function isProblem(value: unknown): value is ProblemDetail {
  return typeof value === "object" && value !== null && "status" in value;
}
```
- Map `errors[].field` to form fields; show `detail` as a general message.
- Show the reference ID of 500 errors so users can report it.
- Never render server messages as HTML (XSS) — use text binding.
- Set request timeouts with `AbortController` / `AbortSignal.timeout(ms)` and cancel requests when components unmount.

---

## 6. Pagination, filtering, sorting

Return a stable, explicit page shape instead of serializing Spring's `PageImpl` (its JSON is not a stable contract):
```java
public record PageResponse<T>(List<T> content, int page, int size, long totalElements, int totalPages) {
    public static <T> PageResponse<T> from(Page<T> p) {
        return new PageResponse<>(p.getContent(), p.getNumber(), p.getSize(),
                p.getTotalElements(), p.getTotalPages());
    }
}
```
(Spring Data also offers `@EnableSpringDataWebSupport(pageSerializationMode = VIA_DTO)` for a stable `PagedModel`.)

- Cap `size` server-side (e.g., max 100).
- For large or fast-changing tables, use **cursor/keyset pagination** (`?after=<lastId>&limit=50`) — `OFFSET` gets slower the deeper you page, and `count(*)` is expensive.
- Sorting: accept only whitelisted field names and map them to entity properties. Never pass raw user input into `Sort.by(...)` or query strings.
- Filtering: explicit query params (`?status=PLACED&from=2026-01-01`) bound to a validated record. For complex search, use Specifications or Querydsl — still with whitelisted fields.

---

## 7. Data types across the wire

| Java | JSON | Frontend | Why |
|---|---|---|---|
| `UUID` | string | `string` | Safe identifier |
| `long` ID | **string** | `string` | JS numbers lose precision above 2^53 − 1 |
| `Instant` | ISO-8601 UTC string `"2026-09-15T08:30:00Z"` | parse with `new Date()` or Temporal | Unambiguous |
| `LocalDate` | `"2026-09-15"` | keep as string or a date lib type | No timezone shift |
| `BigDecimal` money | string `"19.99"` or integer minor units | decimal library if calculating | Floating point is wrong for money |
| `enum` | string name | string union type | Readable, stable |
| `Optional` / null | omit or `null` — be consistent | `T \| undefined` / `T \| null` | Document it in the spec |

```java
public record OrderResponse(
        @JsonFormat(shape = JsonFormat.Shape.STRING) long id,   // only if you use numeric IDs
        ...) {}
```
Spring Boot writes dates as ISO strings by default (not timestamps). Keep it that way.

Adding a field to a response is non-breaking; removing or renaming is breaking. Frontends should ignore unknown fields; the backend should reject unknown fields in requests only if you consciously choose strictness.

---

## 8. Concurrency, idempotency, caching

**Optimistic concurrency (lost-update protection):**
- Return the entity `version` as an `ETag` header on `GET`.
- The client sends `If-Match: "<version>"` on `PUT`/`PATCH`.
- Mismatch → 412 (or 409). The UI tells the user to reload.

**Idempotency for POST (payments, orders):**
- Client generates `Idempotency-Key: <uuid>` per user action and reuses it on retry.
- Server stores key + response for a period and returns the stored response for duplicates.
- Protects against double-clicks and network retries.

**HTTP caching:**
- Static assets: long `Cache-Control: max-age=31536000, immutable` with hashed filenames.
- `index.html`: `no-cache`.
- API responses with personal data: `Cache-Control: no-store` (Spring Security sets no-cache headers by default for authenticated responses).
- Public reference data (countries, product catalog): `Cache-Control: max-age=...` plus ETag.

**Frontend side:** use a data-fetching library (TanStack Query, SWR, Angular's resource/HttpClient patterns) for caching, deduplication, and retries of **GET** requests only.

---

## 9. CORS (when you cannot avoid it)

Only needed when UI and API are on different origins.
```java
@Bean
CorsConfigurationSource corsConfigurationSource(@Value("${app.cors.allowed-origins}") List<String> origins) {
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowedOrigins(origins);                          // exact origins, no "*"
    config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE"));
    config.setAllowedHeaders(List.of("Content-Type", "X-XSRF-TOKEN", "If-Match", "Idempotency-Key"));
    config.setExposedHeaders(List.of("Location", "ETag"));
    config.setAllowCredentials(true);
    config.setMaxAge(Duration.ofHours(1));
    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/api/**", config);
    return source;
}
```
and `http.cors(Customizer.withDefaults())` in the security chain so preflight requests are handled before authentication.

Pitfalls:
- `allowCredentials(true)` + `*` is rejected by browsers and is dangerous; list origins explicitly.
- Never reflect the `Origin` header back blindly.
- Cross-site cookies need `SameSite=None; Secure` — which re-opens CSRF risk. Prefer same-site subdomains (`app.example.com` + `api.example.com` are same-site) or same-origin.
- CORS is not an authorization mechanism; it only controls which browsers may read responses.

---

## 10. Real-time updates

| Need | Choose |
|---|---|
| Server → client notifications, progress, feeds | **Server-Sent Events** (`SseEmitter`) — plain HTTP, auto-reconnect, works with cookies |
| Bidirectional, low latency (chat, collaboration) | WebSocket (Spring WebSocket/STOMP) |
| Occasional refresh | Polling with ETag |

Secure them like any endpoint: authenticate the handshake, authorize each subscription/topic, and validate every inbound message. For WebSockets, check the `Origin` header (Spring does this with `setAllowedOrigins`). With virtual threads, many open SSE connections are cheap on the server.

---

## 11. File upload and download

- Limits: `spring.servlet.multipart.max-file-size` and `max-request-size`.
- Validate type by content (magic bytes, e.g., Apache Tika), not by extension or `Content-Type` header.
- Generate your own storage names; never use the client filename in a filesystem path (path traversal).
- Store outside the web root, ideally in object storage; serve through presigned URLs or a controller that checks authorization.
- Downloads: `Content-Disposition: attachment; filename*=UTF-8''...` and `X-Content-Type-Options: nosniff` to prevent the browser from rendering uploaded HTML as a page.
- Stream large files (`StreamingResponseBody`, `Resource`) instead of loading them into memory.

---

## 12. API versioning

- URL prefix (`/api/v1`) is the most visible and cache-friendly option.
- Spring Framework 7 adds first-class API versioning (header, query param, path, or media type) with a `version` attribute on mapping annotations — verify the configuration properties for your Boot version before relying on them.
- Evolve compatibly first (add fields, add endpoints). Introduce a new version only for breaking changes, and announce deprecation with the `Deprecation` and `Sunset` headers.
