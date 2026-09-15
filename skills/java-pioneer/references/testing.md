# Testing

## Table of contents
1. Strategy
2. Unit tests
3. Web layer tests
4. Security tests
5. Persistence and integration tests with Testcontainers
6. Full-stack and contract tests
7. Architecture tests
8. Test quality rules

---

## 1. Strategy

| Level | Tooling | Speed | Covers |
|---|---|---|---|
| Unit | JUnit Jupiter, AssertJ, Mockito | ms | Domain logic, services with mocked ports |
| Web slice | `@WebMvcTest` + `MockMvcTester` | ~1 s | Mapping, validation, status codes, JSON shape, security rules |
| Persistence slice | `@DataJpaTest` + Testcontainers | seconds | Queries, mappings, migrations |
| Integration | `@SpringBootTest` + Testcontainers | seconds | Wiring, transactions, real infrastructure |
| Contract/E2E | Generated OpenAPI checks, Playwright | slower | Frontend and backend agree |

Spring Boot 4 manages current JUnit, Mockito, AssertJ, and Testcontainers versions — don't override them without a reason. Test slice annotations moved into feature-specific modules/packages in Boot 4; add the matching test starter and let the IDE resolve imports.

Use real databases in tests (Testcontainers), not H2 — H2 hides dialect differences and gives false confidence.

---

## 2. Unit tests

```java
class OrderTest {

    private final ProductCatalog catalog = mock(ProductCatalog.class);

    @Test
    void placingAnOrderCalculatesTheTotal() {
        UUID productId = UUID.randomUUID();
        given(catalog.require(productId)).willReturn(new Product(productId, "Seeds", new BigDecimal("4.50")));

        Order order = Order.place(UUID.randomUUID(), List.of(new OrderLineRequest(productId, 3)), catalog);

        assertThat(order.getTotal()).isEqualByComparingTo("13.50");
        assertThat(order.getStatus()).isEqualTo(OrderStatus.PLACED);
    }

    @Test
    void cancellingAShippedOrderIsRejected() {
        Order order = OrderFixtures.shipped();

        assertThatThrownBy(order::cancel)
                .isInstanceOf(BusinessRuleViolationException.class)
                .hasMessageContaining("shipped");
    }
}
```
- Name tests after behavior, not methods.
- Arrange–Act–Assert with blank lines between.
- `@ParameterizedTest` with `@CsvSource`/`@MethodSource` for rule tables.
- Inject a fixed `Clock` for time logic.
- Mock only what you own at the boundary (ports, clients). Don't mock value objects or the class under test.

---

## 3. Web layer tests

```java
@WebMvcTest(OrderController.class)
@Import(SecurityConfig.class)
class OrderControllerTest {

    @Autowired
    MockMvcTester mvc;

    @MockitoBean
    OrderService orderService;

    @Test
    @WithMockAppUser                                  // custom annotation creating an AppUser principal
    void returnsOrderAsJson() {
        UUID id = UUID.randomUUID();
        given(orderService.find(eq(id), any())).willReturn(OrderFixtures.response(id));

        assertThat(mvc.get().uri("/api/v1/orders/{id}", id))
                .hasStatusOk()
                .bodyJson()
                .extractingPath("$.id").isEqualTo(id.toString());
    }

    @Test
    @WithMockAppUser
    void rejectsInvalidOrderWithProblemDetail() {
        assertThat(mvc.post().uri("/api/v1/orders")
                    .with(csrf())
                    .contentType(MediaType.APPLICATION_JSON)
                    .content("""
                             { "lines": [] }
                             """))
                .hasStatus(HttpStatus.BAD_REQUEST)
                .bodyJson()
                .extractingPath("$.errors[0].field").isEqualTo("lines");
    }
}
```
- `MockMvcTester` (Spring Framework 6.2+) gives fluent AssertJ assertions; classic `MockMvc` still works.
- `@MockitoBean` replaces the removed `@MockBean`.
- Test the JSON contract the frontend relies on: field names, date formats, IDs as strings, error shape.

---

## 4. Security tests

Every protected endpoint deserves at least these cases:
```java
@Test
void anonymousUserGets401() {
    assertThat(mvc.get().uri("/api/v1/orders")).hasStatus(HttpStatus.UNAUTHORIZED);
}

@Test
@WithMockAppUser
void postWithoutCsrfTokenIsForbidden() {
    assertThat(mvc.post().uri("/api/v1/orders")
                .contentType(MediaType.APPLICATION_JSON).content("{}"))
            .hasStatus(HttpStatus.FORBIDDEN);
}

@Test
@WithMockUser(roles = "USER")
void regularUserCannotReachAdminApi() {
    assertThat(mvc.get().uri("/api/admin/users")).hasStatus(HttpStatus.FORBIDDEN);
}
```
And in an integration test: **user B cannot access user A's resource** (expects 404). This one catches IDOR bugs, the most common real vulnerability.

For JWT resource servers use `.with(jwt().authorities(...))` from `SecurityMockMvcRequestPostProcessors`.

---

## 5. Persistence and integration tests with Testcontainers

```java
@TestConfiguration(proxyBeanMethods = false)
class TestcontainersConfig {

    @Bean
    @ServiceConnection
    PostgreSQLContainer postgres() {
        return new PostgreSQLContainer("postgres:17-alpine");
    }
}
```
```java
@DataJpaTest
@Import(TestcontainersConfig.class)
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class OrderRepositoryTest {

    @Autowired OrderRepository orders;

    @Test
    void findsOnlyOrdersOfTheOwner() {
        UUID alice = UUID.randomUUID();
        UUID bob = UUID.randomUUID();
        Order aliceOrder = orders.save(OrderFixtures.placedBy(alice));

        assertThat(orders.findByIdAndOwnerId(aliceOrder.getId(), bob)).isEmpty();
        assertThat(orders.findByIdAndOwnerId(aliceOrder.getId(), alice)).isPresent();
    }
}
```
- `@ServiceConnection` wires the container's URL/credentials automatically — no `@DynamicPropertySource` needed.
- Testcontainers 2.x (used by Spring Boot 4) moved module classes into packages like `org.testcontainers.postgresql`; on 1.x the class is generic (`PostgreSQLContainer<?>`) in `org.testcontainers.containers`. Match the project's version.
- Flyway runs in tests, so migrations are tested too.
- Reuse the same `TestcontainersConfig` for local development: `SpringApplication.from(ShopApplication::main).with(TestcontainersConfig.class).run(args)` in a test-scope `TestShopApplication` gives developers a database with zero setup.
- Keep the application context cacheable: avoid `@DirtiesContext` and too many different `@MockitoBean` combinations — each variation starts a new context and slows the suite.
- Asynchronous behavior: Awaitility, never `Thread.sleep`.

---

## 6. Full-stack and contract tests

- Export the OpenAPI spec in CI and diff it against the committed version (e.g., `openapi-diff` or oasdiff) to catch breaking changes.
- Frontend unit tests mock the API with MSW using types from the generated schema, so mocks break when the contract changes.
- A few Playwright end-to-end tests for critical flows (login, checkout) against a real backend with Testcontainers or docker compose.
- Spring Cloud Contract or Pact when several teams/services depend on each other.

---

## 7. Architecture tests

Enforce the rules from `backend-architecture.md` automatically with ArchUnit:
```java
@AnalyzeClasses(packages = "com.example.shop")
class ArchitectureTest {

    @ArchTest
    static final ArchRule controllersDoNotUseRepositories =
            noClasses().that().haveSimpleNameEndingWith("Controller")
                    .should().dependOnClassesThat().haveSimpleNameEndingWith("Repository");

    @ArchTest
    static final ArchRule noFieldInjection =
            noFields().should().beAnnotatedWith(Autowired.class);
}
```
Spring Modulith's `ApplicationModules.of(ShopApplication.class).verify()` checks module boundaries in package-by-feature layouts.

---

## 8. Test quality rules

- Tests must be deterministic: no reliance on execution order, current time, random data without a seed, or external services.
- One behavior per test; the name explains the failure without reading the code.
- Prefer test data builders/fixtures over giant setup methods.
- Coverage is a signal, not a goal. Use mutation testing (PIT) on core domain logic to see if tests actually detect bugs.
- Run fast tests on every commit; integration tests in CI on every push (Testcontainers works in GitHub Actions/GitLab CI).
- A bug fix starts with a failing test that reproduces the bug.
