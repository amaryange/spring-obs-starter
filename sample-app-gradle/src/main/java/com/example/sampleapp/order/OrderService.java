package com.example.sampleapp.order;

import io.micrometer.observation.annotation.Observed;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Demonstrates @Observed: Spring Boot 4 automatically creates a span AND a
 * Micrometer timer for each annotated method, with no instrumentation code.
 */
@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private static final Map<Long, Order> STORE = Map.of(
            1L, new Order(1L, "Spring Boot Sticker Pack", new BigDecimal("9.99"), "DELIVERED"),
            2L, new Order(2L, "Grafana T-Shirt", new BigDecimal("29.99"), "PENDING"),
            3L, new Order(3L, "OTel Collector Mug", new BigDecimal("14.99"), "SHIPPED")
    );

    @Observed(name = "order.list", contextualName = "listing-all-orders")
    public List<Order> findAll() {
        log.info("Fetching all orders — count={}", STORE.size());
        return List.copyOf(STORE.values());
    }

    @Observed(name = "order.find", contextualName = "finding-order-by-id")
    public Order findById(Long id) {
        Order order = STORE.get(id);
        if (order == null) {
            log.warn("Order not found — id={}", id);
            throw new OrderNotFoundException(id);
        }
        log.info("Order found — id={} product={} status={}", order.id(), order.product(), order.status());
        return order;
    }

    @Observed(name = "order.process.slow", contextualName = "processing-slow-order")
    public Order processSlowOrder() throws InterruptedException {
        long delayMs = ThreadLocalRandom.current().nextLong(500, 2000);
        log.info("Processing slow order — simulatedDelayMs={}", delayMs);
        Thread.sleep(delayMs);
        log.info("Slow order processing complete — delayMs={}", delayMs);
        return new Order(99L, "Delayed Delivery Box", new BigDecimal("49.99"), "PROCESSING");
    }
}
