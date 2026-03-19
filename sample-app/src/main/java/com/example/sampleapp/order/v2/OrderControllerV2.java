package com.example.sampleapp.order.v2;

import com.example.sampleapp.order.OrderService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * V2 order endpoints — enriched responses (currency, VAT, createdAt).
 *
 * Breaking change strategy: V1 stays frozen at /api/v1/orders.
 * New consumers target /api/v2/orders from the start.
 */
@RestController
@RequestMapping("/api/v2/orders")
public class OrderControllerV2 {

    private final OrderService orderService;

    public OrderControllerV2(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping
    public List<OrderResponseV2> listOrders() {
        return orderService.findAll().stream()
                .map(OrderResponseV2::from)
                .toList();
    }

    @GetMapping("/{id}")
    public OrderResponseV2 getOrder(@PathVariable Long id) {
        return OrderResponseV2.from(orderService.findById(id));
    }

    /**
     * Slow endpoint preserved in V2 — useful for latency comparison across versions.
     */
    @GetMapping("/slow")
    public OrderResponseV2 slowOrder() throws InterruptedException {
        return OrderResponseV2.from(orderService.processSlowOrder());
    }
}
