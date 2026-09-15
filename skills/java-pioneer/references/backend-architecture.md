# Spring Boot Backend Architecture

## Table of contents
1. Layers and responsibilities
2. Controller
3. DTOs and mapping
4. Service and transactions
5. Entities and repositories
6. Error handling with ProblemDetail
7. Configuration
8. Outgoing HTTP calls
9. Database migrations
10. Observability and operations
11. Spring Boot 4 migration notes

---

## 1. Layers and responsibilities

| Layer | Does | Never does |
|---|---|---|
| Controller | HTTP mapping, `@Valid`, resolve current user, call one service method, return DTO | Business logic, repository calls, transactions |
| Service | Business rules, authorization on data, transactions, orchestration | Know about `HttpServletRequest`, return entities to controllers |
| Repository | Data access queries | Business logic |
| Domain/entity | Invariants of its own state | Call services or repositories |

Keep features isolated (package by feature). If a module grows large, consider Spring Modulith to verify module boundaries in tests.

---

## 2. Controller

```java
// order/OrderController.java
@RestController
@RequestMapping("/api/v1/orders")
class OrderController {

    private final OrderService orderService;

    OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/{id}")
    OrderResponse get(@PathVariable UUID id, @AuthenticationPrincipal AppUser user) {
        return orderService.find(id, user.id());
    }

    @GetMapping
    PageResponse<OrderSummary> list(
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
            @AuthenticationPrincipal AppUser user) {
        return orderService.list(user.id(), page, size);
    }

    @PostMapping
    ResponseEntity<OrderResponse> create(@Valid @RequestBody CreateOrderRequest request,
                                         @AuthenticationPrincipal AppUser user) {
        OrderResponse created = orderService.create(request, user.id());
        URI location = URI.create("/api/v1/orders/" + created.id());
        return ResponseEntity.created(location).body(created);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void cancel(@PathVariable UUID id, @AuthenticationPrincipal AppUser user) {
        orderService.cancel(id, user.id());
    }
}
```
Notes:
- Method-level constraints like `@Min`/`@Max` on parameters are validated by Spring MVC's built-in method validation (Framework 6.1+) and raise `HandlerMethodValidationException`.
- Return `ResponseEntity` only when you need headers or dynamic status; otherwise return the DTO.
- `AppUser` is your own `UserDetails` implementation (or a principal extracted from a JWT). Never trust a user ID sent in the request body.

---

## 3. DTOs and mapping

```java
// order/dto/CreateOrderRequest.java
public record CreateOrderRequest(
        @NotEmpty @Size(max = 50) List<@Valid OrderLineRequest> lines,
        @Size(max = 500) String note) {}

public record OrderLineRequest(
        @NotNull UUID productId,
        @Positive @Max(1000) int quantity) {}

// order/dto/OrderResponse.java
public record OrderResponse(UUID id, OrderStatus status, BigDecimal total,
                            Instant createdAt, List<OrderLineResponse> lines) {

    static OrderResponse from(Order order) {
        return new OrderResponse(order.getId(), order.getStatus(), order.getTotal(),
                order.getCreatedAt(),
                order.getLines().stream().map(OrderLineResponse::from).toList());
    }
}
```
- Separate request and response DTOs. Requests contain only fields the client may set (prevents mass assignment: a client can never send `status` or `ownerId`).
- Manual static factory methods are fine for small projects. Use MapStruct when mappings get numerous; it generates plain code at compile time (no reflection).
- Always bound sizes (`@Size`, `@Max`) — unbounded lists and strings are a denial-of-service vector.

---

## 4. Service and transactions

```java
@Service
@Transactional(readOnly = true)
public class OrderService {

    private final OrderRepository orders;
    private final ProductCatalog catalog;
    private final ApplicationEventPublisher events;

    public OrderService(OrderRepository orders, ProductCatalog catalog, ApplicationEventPublisher events) {
        this.orders = orders;
        this.catalog = catalog;
        this.events = events;
    }

    public OrderResponse find(UUID id, UUID ownerId) {
        return orders.findByIdAndOwnerId(id, ownerId)          // ownership in the query = no IDOR
                .map(OrderResponse::from)
                .orElseThrow(() -> new NotFoundException("Order not found"));
    }

    @Transactional
    public OrderResponse create(CreateOrderRequest request, UUID ownerId) {
        Order order = Order.place(ownerId, request.lines(), catalog);   // domain logic in the entity
        orders.save(order);
        events.publishEvent(new OrderPlaced(order.getId()));
        return OrderResponse.from(order);
    }
}
```
Rules:
- `@Transactional(readOnly = true)` at class level, `@Transactional` on writing methods. Read-only lets Hibernate skip dirty checking and lets the driver route to replicas.
- Transactions work through proxies: calling a `@Transactional` method from the same class bypasses the proxy. Split into another bean if needed.
- By default only unchecked exceptions roll back.
- Never call slow external services inside a transaction — it holds a DB connection the whole time. Use `@TransactionalEventListener(phase = AFTER_COMMIT)` for side effects (emails, messages).
- For reliable messaging, use the transactional outbox pattern instead of "save then send".

---

## 5. Entities and repositories

```java
@Entity
@Table(name = "orders")
public class Order {

    @Id
    private UUID id;

    @Column(nullable = false)
    private UUID ownerId;

    @Enumerated(EnumType.STRING)          // never ORDINAL — reordering the enum corrupts data
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal total;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderLine> lines = new ArrayList<>();

    @Version                               // optimistic locking
    private long version;

    private Instant createdAt;

    protected Order() {}                   // for JPA only

    public static Order place(UUID ownerId, List<OrderLineRequest> requested, ProductCatalog catalog) {
        Order order = new Order();
        order.id = UUID.randomUUID();      // or UUIDv7 for index-friendly ordering
        order.ownerId = ownerId;
        order.status = OrderStatus.PLACED;
        order.createdAt = Instant.now();
        requested.forEach(r -> order.addLine(catalog.require(r.productId()), r.quantity()));
        order.total = order.lines.stream().map(OrderLine::subtotal).reduce(BigDecimal.ZERO, BigDecimal::add);
        return order;
    }

    // equals/hashCode based on id only (id is assigned in the factory, so it's stable)
    @Override public boolean equals(Object o) { return o instanceof Order other && id.equals(other.id); }
    @Override public int hashCode() { return id.hashCode(); }

    // getters only; state changes go through intention-revealing methods like cancel()
}
```
- All associations `LAZY` (`@ManyToOne(fetch = FetchType.LAZY)` — the JPA default for `ToOne` is EAGER, change it).
- No Lombok `@Data`/`@EqualsAndHashCode` on entities; `@Getter` is acceptable.
- Assign IDs in the application (UUID) or use `SEQUENCE` generation. `IDENTITY` disables JDBC batch inserts.

```java
interface OrderRepository extends JpaRepository<Order, UUID> {

    Optional<Order> findByIdAndOwnerId(UUID id, UUID ownerId);

    @Query("""
           select new com.example.shop.order.dto.OrderSummary(o.id, o.status, o.total, o.createdAt)
           from Order o
           where o.ownerId = :ownerId
           order by o.createdAt desc
           """)
    Page<OrderSummary> findSummaries(@Param("ownerId") UUID ownerId, Pageable pageable);

    @EntityGraph(attributePaths = "lines")
    Optional<Order> findWithLinesById(UUID id);
}
```
Consider jOOQ or `JdbcClient` for reporting-heavy or complex SQL — JPA is not the right tool for everything.

---

## 6. Error handling with ProblemDetail (RFC 9457)

```yaml
spring:
  mvc:
    problemdetails:
      enabled: true
```

```java
// common/ApiExceptionHandler.java
@RestControllerAdvice
class ApiExceptionHandler extends ResponseEntityExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(NotFoundException.class)
    ProblemDetail notFound(NotFoundException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setTitle("Resource not found");
        pd.setType(URI.create("https://api.example.com/problems/not-found"));
        return pd;
    }

    @ExceptionHandler({ConflictException.class, ObjectOptimisticLockingFailureException.class})
    ProblemDetail conflict(RuntimeException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
                "The resource was changed by someone else. Reload and try again.");
        pd.setTitle("Conflict");
        return pd;
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        ProblemDetail pd = ex.getBody();
        pd.setTitle("Validation failed");
        pd.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
                .map(fe -> Map.of(
                        "field", fe.getField(),
                        "message", Objects.requireNonNullElse(fe.getDefaultMessage(), "invalid")))
                .toList());
        return handleExceptionInternal(ex, pd, headers, status, request);
    }

    @ExceptionHandler(Exception.class)
    ProblemDetail unexpected(Exception ex) throws Exception {
        // Let Spring Security translate these into 401/403 — otherwise they become 500s.
        if (ex instanceof AccessDeniedException || ex instanceof AuthenticationException) {
            throw ex;
        }
        String errorId = UUID.randomUUID().toString();
        log.error("Unhandled error [{}]", errorId, ex);
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
                "Unexpected error. Reference: " + errorId);
        pd.setTitle("Internal error");
        return pd;
    }
}
```
- Also override `handleHandlerMethodValidationException` if you use parameter constraints and want the same `errors` format.
- Messages in `detail` must be safe for end users: no SQL, class names, or stack traces.
- Keep `type` URIs stable — the frontend can switch on them.

---

## 7. Configuration

```java
@ConfigurationProperties(prefix = "shop.payment")
@Validated
public record PaymentProperties(
        @NotNull URI baseUrl,
        @NotNull Duration connectTimeout,
        @NotNull Duration readTimeout,
        @NotBlank String apiKey) {}
```
Enable with `@ConfigurationPropertiesScan` on the application class.
```yaml
shop:
  payment:
    base-url: https://pay.example.com
    connect-timeout: 2s
    read-timeout: 5s
    api-key: ${PAYMENT_API_KEY}        # from environment, never committed

spring:
  jpa:
    open-in-view: false
    hibernate:
      ddl-auto: validate
  threads:
    virtual:
      enabled: true
server:
  shutdown: graceful
  error:
    include-stacktrace: never
    include-message: never
```
- Typed, validated properties fail at startup instead of at 3 a.m.
- Use profiles (`application-local.yml`) only for environment differences, not feature flags.

---

## 8. Outgoing HTTP calls

Use `RestClient` (synchronous, fits virtual threads) or declarative HTTP interfaces:

```java
@HttpExchange("/v1/payments")
public interface PaymentClient {
    @PostExchange
    PaymentResult charge(@RequestBody ChargeRequest request);
}

@Configuration
class PaymentClientConfig {
    @Bean
    PaymentClient paymentClient(RestClient.Builder builder, PaymentProperties props) {
        HttpClient jdkClient = HttpClient.newBuilder()
                .connectTimeout(props.connectTimeout())
                .build();
        var requestFactory = new JdkClientHttpRequestFactory(jdkClient);
        requestFactory.setReadTimeout(props.readTimeout());

        RestClient client = builder
                .baseUrl(props.baseUrl().toString())
                .defaultHeader("Authorization", "Bearer " + props.apiKey())
                .requestFactory(requestFactory)
                .build();
        return HttpServiceProxyFactory.builderFor(RestClientAdapter.create(client))
                .build().createClient(PaymentClient.class);
    }
}
```
- **Always set timeouts.** A missing read timeout eventually exhausts your server.
- Spring Boot 4 also offers `@ImportHttpServices` to register HTTP interface clients with less code — verify the exact API for your version.
- Add retries only for idempotent operations, with backoff and jitter (Spring Framework 7 has built-in `@Retryable` / resilience features; Resilience4j is the established alternative for circuit breakers).
- Always inject `RestClient.Builder` so observability (tracing, metrics) is applied automatically.

---

## 9. Database migrations

- Flyway (or Liquibase) is the single source of truth for the schema: `src/main/resources/db/migration/V1__create_orders.sql`.
- Never edit an applied migration; add a new one.
- Make migrations backward compatible for rolling deployments (expand → migrate → contract).
- Create indexes for every foreign key and every column used in `WHERE`/`ORDER BY` of hot queries.

---

## 10. Observability and operations

- `spring-boot-starter-actuator` + Micrometer (Prometheus registry) + tracing via OpenTelemetry.
- Expose only what you need:
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  endpoint:
    health:
      probes:
        enabled: true            # /actuator/health/liveness and /readiness for Kubernetes
      show-details: when-authorized
```
- Consider running management endpoints on a separate port (`management.server.port`) that is not publicly routed.
- Graceful shutdown + readiness probes = zero-downtime deployments.

---

## 11. Spring Boot 4 migration notes (from 3.x)

Verify each point in the official migration guide for the exact version:
- Jackson 3 is the default JSON library (`tools.jackson.*` packages for databind; the annotations stay in `com.fasterxml.jackson.annotation`).
- Starters and auto-configuration are more modular; some classes and test annotations moved packages — let the IDE re-resolve imports.
- `@MockBean`/`@SpyBean` are gone → use `@MockitoBean`/`@MockitoSpyBean`.
- Spring Security 7: lambda DSL only (no `.and()` chaining), `authorizeHttpRequests` only.
- Jakarta EE 11 baseline (Servlet 6.1, JPA 3.2, Bean Validation 3.1), Hibernate 7.
- JSpecify null-safety annotations replace Spring's own `@Nullable`.
- Built-in API versioning support in Spring MVC (Framework 7).
- Use the `spring-boot-properties-migrator` dependency temporarily to find renamed properties.
