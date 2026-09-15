package demo;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/orders")
class OrderController {
    private final OrderService orders;
    OrderController(OrderService orders) { this.orders = orders; }

    @GetMapping("/{id}")
    OrderResponse get(@PathVariable UUID id) { return orders.find(id); }

    @PostMapping
    OrderResponse create(@Valid @RequestBody CreateOrderRequest req) { return orders.create(req); }
}
