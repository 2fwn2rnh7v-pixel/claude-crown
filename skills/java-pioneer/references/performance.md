# Performance

## Table of contents
1. Method: measure, don't guess
2. Database and JPA
3. Connection pool and threads
4. Caching
5. HTTP layer
6. JVM and container settings
7. Startup time and memory footprint
8. Frontend-side performance with a Java API
9. Load and micro-benchmarking

---

## 1. Method: measure, don't guess

1. Define a target (e.g., p95 < 200 ms at 300 req/s).
2. Reproduce with a load test.
3. Find the bottleneck with data:
   - **Micrometer + Prometheus/Grafana:** `http.server.requests` percentiles, `hikaricp.connections.pending`, JVM memory/GC.
   - **Tracing (OpenTelemetry):** where time goes across services and queries.
   - **Java Flight Recorder:** `jcmd <pid> JFR.start duration=60s filename=rec.jfr`, analyze in JDK Mission Control. Low overhead, safe in production.
   - **async-profiler:** CPU/allocation flame graphs.
   - **SQL logging in dev:** `spring.jpa.properties.hibernate.generate_statistics=true`, or datasource-proxy to count queries per request.
4. Fix the biggest bottleneck, measure again. In typical web apps it is almost always the database.

---

## 2. Database and JPA

### N+1 queries
Symptom: one query for the list, then one per row for an association.
Fixes (pick per use case):
```java
@EntityGraph(attributePaths = {"customer", "lines"})
List<Order> findByStatus(OrderStatus status);

@Query("select distinct o from Order o join fetch o.lines where o.id in :ids")
List<Order> findWithLines(@Param("ids") Collection<UUID> ids);
```
```yaml
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 50     # loads lazy collections in batches instead of one by one
```
Don't fetch-join a collection together with pagination — Hibernate paginates in memory (warning HHH90003004). Page the IDs first, then fetch the details for those IDs.

### Read models
For lists and dashboards, select only needed columns into records (JPQL constructor expressions, interface/record projections, or `JdbcClient`). No entity management overhead, no lazy-loading surprises.

### Writes in bulk
```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 50
        order_inserts: true
        order_updates: true
```
- Batching doesn't work with `GenerationType.IDENTITY` — use app-assigned UUIDs or `SEQUENCE` with `allocationSize` matching the sequence increment.
- For large imports, flush and clear the persistence context every N entities, or use `JdbcClient`/`COPY` directly.
- Bulk updates: a single `update ... where ...` statement (`@Modifying` query) instead of loading entities.

### Indexes and queries
- Index foreign keys and hot `WHERE`/`ORDER BY` columns; composite index order matters.
- Check plans with `EXPLAIN (ANALYZE, BUFFERS)` in PostgreSQL.
- Avoid `OFFSET` for deep pagination → keyset pagination.
- Avoid `count(*)` on huge tables for every page → use `Slice` or cursor pagination.
- Random UUIDv4 primary keys fragment B-tree indexes on very large tables; UUIDv7 (time-ordered) avoids that.

### Transactions
- Keep them short. No remote calls, file I/O, or user think-time inside.
- `@Transactional(readOnly = true)` for reads.
- `open-in-view=false` so connections aren't held during JSON serialization.

---

## 3. Connection pool and threads

- HikariCP is the default. Start small: pool size ≈ `(CPU cores of the DB × 2) + effective spindles` is a classic starting point; for most services 10–30 is plenty. A bigger pool often makes the database slower.
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 20
      connection-timeout: 3000       # ms; fail fast instead of piling up requests
      max-lifetime: 1500000          # below the DB/proxy idle cutoff
```
- Virtual threads (`spring.threads.virtual.enabled=true`): thousands of concurrent requests are cheap, but they all compete for the same 20 connections. Watch `hikaricp.connections.pending` and time out fast.
- Separate pools/bulkheads for slow downstream dependencies so one slow service can't starve everything.
- WebFlux (reactive) is rarely worth its complexity since virtual threads; choose it only for streaming-heavy workloads or when the team already knows it well.

---

## 4. Caching

Order of preference:
1. **HTTP caching** (browser/CDN) — cheapest, see `frontend-integration.md`.
2. **In-process cache** (Caffeine) — reference data, per-instance, microsecond access.
3. **Distributed cache** (Redis) — shared across instances, sessions, rate limits.

```java
@Configuration
@EnableCaching
class CacheConfig {
    @Bean
    CacheManager cacheManager() {
        CaffeineCacheManager manager = new CaffeineCacheManager("products", "countries");
        manager.setCaffeine(Caffeine.newBuilder()
                .maximumSize(10_000)
                .expireAfterWrite(Duration.ofMinutes(10))
                .recordStats());
        return manager;
    }
}

@Cacheable(cacheNames = "products", key = "#id")
public ProductResponse find(UUID id) { ... }

@CacheEvict(cacheNames = "products", key = "#id")
public void update(UUID id, UpdateProductRequest req) { ... }
```
Rules:
- Always bound size and set expiry.
- Cache immutable DTOs, not managed entities.
- Never cache user-specific data under a key that ignores the user.
- Cache invalidation must be designed, not hoped for. With multiple instances, local caches drift — keep TTLs short or use Redis/pub-sub eviction.
- Hibernate second-level cache: only for read-mostly entities, and only after measuring.

---

## 5. HTTP layer

```yaml
server:
  compression:
    enabled: true
    mime-types: application/json,application/problem+json,text/html,text/css,application/javascript
    min-response-size: 1024
  http2:
    enabled: true          # requires TLS at the app, or terminate HTTP/2 at the proxy
```
- Keep payloads lean: only fields the UI needs, paginate, avoid deeply nested graphs.
- `ShallowEtagHeaderFilter` saves bandwidth (304 responses) but still computes the full response; real savings come from version-based ETags checked before loading data.
- Stream large responses (`StreamingResponseBody`, SSE) instead of buffering.
- Configure Tomcat limits consciously (`server.tomcat.max-connections`, `accept-count`, `connection-timeout`).
- Set timeouts on every outbound client (see `backend-architecture.md`).

---

## 6. JVM and container settings

- Use a current LTS JDK — every release brings free GC and JIT improvements.
- Containers: the JVM respects cgroup limits. Size the heap relative to the container:
```
-XX:MaxRAMPercentage=75
```
- GC choice:
  - **G1** (default): good balance for most services.
  - **Generational ZGC** (`-XX:+UseZGC`; generational is the only mode since JDK 24): sub-millisecond pauses for large heaps and latency-sensitive services.
  - **Parallel GC**: max throughput for batch jobs.
  - **Serial GC**: tiny containers (< 2 CPUs, small heap).
- Java 25: `-XX:+UseCompactObjectHeaders` reduces object header size, often lowering heap usage noticeably — test before enabling in production.
- Always enable heap dumps on OOM to a writable volume: `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps`.
- Don't tune dozens of flags blindly. Change one thing, measure.

---

## 7. Startup time and memory footprint

| Technique | Effect | Cost |
|---|---|---|
| Lazy init only where safe (`spring.main.lazy-initialization`) | Faster startup | Errors surface later; usually avoid in prod |
| CDS / AOT cache (JDK 24+ JEP 483; JDK 25 simplifies creation with `-XX:AOTCacheOutput`) | Much faster startup, same JVM | Training run in the build |
| Spring AOT + GraalVM native image | Very fast startup, low memory | Long builds, reflection config, no JIT peak performance |
| CRaC (checkpoint/restore) | Near-instant startup | Special JDK builds, careful resource handling |

Spring Boot documents how to create the CDS/AOT cache from an extracted jar — follow the guide for your version. Choose native images for scale-to-zero/serverless; choose JIT for long-running high-throughput services.

---

## 8. Frontend-side performance with a Java API

- Avoid request waterfalls: fire independent requests in parallel (`Promise.all`) or offer a purpose-built endpoint.
- Debounce search inputs (≈300 ms) and cancel stale requests with `AbortController`.
- Cache GET responses client-side (TanStack Query etc.) with sensible `staleTime`.
- Use cursor pagination / infinite scroll with virtualization for long lists.
- Prefetch on hover/route intent for likely navigations.
- Compress and fingerprint static assets; serve them from a CDN with long cache lifetimes.
- Don't poll aggressively; use SSE for push.

---

## 9. Load and micro-benchmarking

- **Load tests:** Gatling (Java/Kotlin DSL — fits Java teams), k6, or JMeter. Test realistic scenarios with think time, a production-like database size, and warm-up.
- **Micro-benchmarks:** JMH only. Never benchmark with `System.nanoTime()` loops — JIT warm-up and dead-code elimination make results meaningless.
- Track performance in CI for critical paths to catch regressions.
