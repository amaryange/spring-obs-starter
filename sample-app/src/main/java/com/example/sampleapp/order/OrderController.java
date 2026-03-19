package com.example.sampleapp.order;

import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * V1 order endpoints — stable, no breaking changes.
 * V2 adds enriched response fields (currency, createdAt, amountWithTax).
 */
@RestController
@RequestMapping("/api/v1/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping
    public List<Order> listOrders() {
        return orderService.findAll();
    }

    @GetMapping("/{id}")
    public Order getOrder(@PathVariable Long id) {
        return orderService.findById(id);
    }

    /**
     * Demonstrates a slow endpoint — useful to observe p95/p99 latency in Grafana.
     */
    @GetMapping("/slow")
    public Order slowOrder() throws InterruptedException {
        return orderService.processSlowOrder();
    }

}