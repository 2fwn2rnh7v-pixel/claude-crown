# Modern Java (21 → 25 LTS)

## Table of contents
1. Feature availability by version
2. Data modeling: records, sealed types, pattern matching
3. Null handling and Optional
4. Collections and streams
5. Concurrency: virtual threads, structured concurrency, scoped values
6. Exceptions
7. Strings, dates, money
8. Logging
9. Naming and style
10. Things that are gone or discouraged

---

## 1. Feature availability by version

Check `maven.compiler.release` / `java.toolchain.languageVersion` before using a feature. Never enable preview features in production code unless the user explicitly wants that.

| Feature | Final in | Notes |
|---|---|---|
| Records, sealed classes, text blocks, `instanceof` patterns | 16–17 | Safe everywhere on 17+ |
| Virtual threads (JEP 444) | 21 | Pinning on `synchronized` fixed in 24 (JEP 491) |
| Pattern matching for `switch`, record patterns | 21 | |
| Sequenced collections (`getFirst()`, `getLast()`, `reversed()`) | 21 | |
| Unnamed variables and patterns `_` (JEP 456) | 22 | |
| Foreign Function & Memory API (JEP 454) | 22 | Replacement for most JNI use |
| Stream gatherers (JEP 485) | 24 | Custom intermediate stream ops |
| Security Manager permanently disabled (JEP 486) | 24 | |
| Scoped values (JEP 506) | 25 | Replacement for many `ThreadLocal` uses |
| Flexible constructor bodies (JEP 513) | 25 | Statements before `super(...)` |
| Module import declarations (JEP 511) | 25 | `import module java.base;` |
| Compact source files & instance main methods (JEP 512) | 25 | Great for scripts, not for services |
| Compact object headers (JEP 519) | 25 (product flag) | `-XX:+UseCompactObjectHeaders` |
| Structured concurrency | Preview in 25 | Do not use without `--enable-preview` consent |

---

## 2. Data modeling

### Records for DTOs and value objects
```java
public record Money(BigDecimal amount, Currency currency) {
    public Money {                       // compact constructor = invariant check
        Objects.requireNonNull(amount, "amount");
        Objects.requireNonNull(currency, "currency");
        if (amount.scale() > currency.getDefaultFractionDigits()) {
            throw new IllegalArgumentException("Too many decimal places for " + currency);
        }
    }

    public Money plus(Money other) {
        if (!currency.equals(other.currency)) throw new IllegalArgumentException("Currency mismatch");
        return new Money(amount.add(other.amount), currency);
    }
}
```
Defensive-copy mutable components: `items = List.copyOf(items);` inside the compact constructor.

Records are **not** good JPA entities (entities need a no-arg constructor and mutable state). Records are perfect for DTOs, projections, config properties, events, and value objects (`@Embeddable` records are supported by Hibernate 6.2+).

### Sealed types + exhaustive switch
Model closed sets of outcomes so the compiler finds missing cases:
```java
public sealed interface PaymentResult permits Approved, Declined, RequiresAction {}
public record Approved(String transactionId) implements PaymentResult {}
public record Declined(String reason) implements PaymentResult {}
public record RequiresAction(URI redirectUrl) implements PaymentResult {}

String describe(PaymentResult result) {
    return switch (result) {                       // no default → compiler checks exhaustiveness
        case Approved(var id)         -> "Paid: " + id;
        case Declined(var reason)     -> "Declined: " + reason;
        case RequiresAction(var url)  -> "Continue at " + url;
    };
}
```
Avoid a `default` branch on sealed types — it silences the compiler when a new subtype is added.

### Guards and unnamed patterns
```java
return switch (event) {
    case OrderPlaced p when p.total().compareTo(LIMIT) > 0 -> review(p);
    case OrderPlaced p -> accept(p);
    case OrderCancelled _ -> ignore();
};
```

---

## 3. Null handling and Optional

- Spring Framework 7 / Boot 4 use **JSpecify** annotations. Put `@NullMarked` in `package-info.java` so everything is non-null by default, and mark exceptions with `@Nullable` (`org.jspecify.annotations`). Tools like NullAway can then enforce it at compile time.
- `Optional` is for **return values** that may be absent. Not for fields, parameters, or collections.
- Never call `optional.get()` without a check; use `orElseThrow(...)`, `map`, `ifPresentOrElse`.
- Return empty collections, never `null`.
- Use `Objects.requireNonNull(x, "x")` at public API boundaries.

```java
// package-info.java
@NullMarked
package com.example.shop.order;

import org.jspecify.annotations.NullMarked;
```

---

## 4. Collections and streams

- Use `List.of`, `Set.of`, `Map.of` for immutable literals (they reject `null`).
- `List.copyOf(list)` for defensive copies; `stream.toList()` returns an unmodifiable list.
- Sequenced collections: `list.getFirst()`, `list.getLast()`, `list.reversed()` instead of `get(0)` / `get(size-1)`.
- Streams for transformations; plain loops when you need early exit, checked exceptions, or complex state. Readability decides.
- Never mutate external state inside `stream().forEach(...)`.
- `parallelStream()` almost never helps in a web server — the request threads are already parallel. Only use it for CPU-heavy work on large data after measuring.
- Pre-size `HashMap`/`ArrayList` when size is known: `HashMap.newHashMap(expected)` (Java 19+).

```java
Map<Status, List<OrderSummary>> byStatus = orders.stream()
        .collect(Collectors.groupingBy(OrderSummary::status));
```

---

## 5. Concurrency

### Virtual threads (Java 21+)
- In Spring Boot: `spring.threads.virtual.enabled=true` switches Tomcat request handling, `@Async`, and scheduling to virtual threads.
- Standalone: `try (var executor = Executors.newVirtualThreadPerTaskExecutor()) { ... }`.
- **Never pool virtual threads.** Create one per task; they are cheap.
- **Bound access to scarce resources** (DB connections, rate-limited APIs) with a `Semaphore` or the connection pool itself. Virtual threads remove the natural throttle that a 200-thread pool gave you.
- On Java 21–23, `synchronized` around blocking I/O pins the carrier thread → prefer `ReentrantLock`. On 24+ this is fixed (JEP 491), but native calls can still pin.
- Avoid large `ThreadLocal` caches — with millions of threads they multiply memory. Prefer scoped values on 25+.
- Virtual threads help **I/O-bound** work. They do nothing for CPU-bound work.

### Parallel remote calls without preview APIs
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    Future<Customer> customer = executor.submit(() -> customerClient.find(id));
    Future<List<Order>> orders = executor.submit(() -> orderClient.findByCustomer(id));
    return new Dashboard(customer.get(2, SECONDS), orders.get(2, SECONDS));
}
```
Always set timeouts. `CompletableFuture` remains fine for composition-heavy code.

### Scoped values (Java 25)
```java
static final ScopedValue<RequestContext> CONTEXT = ScopedValue.newInstance();

ScopedValue.where(CONTEXT, ctx).run(() -> service.handle());
// deeper in the call stack:
RequestContext ctx = CONTEXT.get();
```
Immutable, automatically cleaned up, and cheap to inherit — unlike `ThreadLocal`.

### General rules
- Prefer immutable data and message passing over shared mutable state.
- Use `java.util.concurrent` types (`ConcurrentHashMap`, `AtomicLong`, `LongAdder`) instead of manual locking.
- Never use `Thread.sleep` for coordination.
- Always handle `InterruptedException` by restoring the flag: `Thread.currentThread().interrupt();`.

---

## 6. Exceptions

- Use unchecked domain exceptions (`NotFoundException`, `ConflictException`, `BusinessRuleViolationException`) and translate them to HTTP in one place (`@RestControllerAdvice`).
- Wrap low-level exceptions with context, keep the cause: `throw new StorageException("Could not store invoice " + id, e);`
- Never swallow exceptions. Never log *and* rethrow the same exception (duplicate logs).
- Use try-with-resources for everything `AutoCloseable`.
- Don't use exceptions for normal control flow.

---

## 7. Strings, dates, money

- Text blocks for SQL, JSON, and HTML snippets in tests.
- `String.formatted(...)` or `StringBuilder`; no `+` in loops.
- Dates: `java.time` only. Store and transmit **`Instant`** (UTC) for points in time; `LocalDate` for calendar dates; convert to a `ZoneId` only for display. Never `java.util.Date` in new code.
- Inject a `Clock` bean so time-dependent logic is testable.
- Money: `BigDecimal` with explicit `RoundingMode`, compare with `compareTo`, never `double`. Create from strings: `new BigDecimal("19.99")`.
- Compare strings with `equals`; use `equalsIgnoreCase` or `Locale.ROOT` for case-insensitive logic (avoid the Turkish-i bug).

---

## 8. Logging

```java
private static final Logger log = LoggerFactory.getLogger(OrderService.class);

log.info("Order {} created for customer {}", order.id(), customerId);   // parameterized
log.warn("Payment provider slow: {} ms", elapsed);
log.error("Failed to publish order {}", order.id(), exception);         // exception last
```
- SLF4J API, Logback (Spring default). Structured JSON logs in production (`logging.structured.format.console=ecs` or `logstash` in Spring Boot 3.4+).
- Never log passwords, tokens, full card numbers, or personal data. Mask or omit.
- Use MDC (or Micrometer tracing) for request/trace IDs.

---

## 9. Naming and style

- Classes are nouns (`InvoiceGenerator`), methods are verbs (`calculateTotal`).
- Booleans read like questions: `isActive`, `hasPermission`.
- No abbreviations except well-known ones (`id`, `url`, `dto`).
- Keep methods short and at one level of abstraction.
- `var` when the type is obvious from the right-hand side; spell out the type otherwise.
- Minimize visibility: package-private classes are fine and encouraged in package-by-feature layouts.
- Format with a tool (Spotless + google-java-format or palantir-java-format) so style is never a review topic.

---

## 10. Gone or discouraged

- `SecurityManager` — permanently disabled (Java 24).
- `finalize()` — deprecated for removal; use `Cleaner` or try-with-resources.
- Java serialization (`Serializable` + `ObjectInputStream`) for external data — a classic RCE vector. Use JSON/Protobuf.
- `new Integer(...)`, `new Long(...)` constructors — deprecated; use `valueOf`.
- String templates — the preview was withdrawn; don't use them.
- `Vector`, `Hashtable`, `Stack` — use modern collections.
- `java.util.Date`, `Calendar`, `SimpleDateFormat` (not thread-safe) — use `java.time`.
