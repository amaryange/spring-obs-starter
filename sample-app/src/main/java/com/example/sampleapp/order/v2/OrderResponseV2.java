package com.example.sampleapp.order.v2;

import com.example.sampleapp.order.Order;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;

/**
 * V2 order response — adds currency, createdAt, and amountWithTax (20% VAT).
 *
 * V1 → V2 evolution: new fields are additive, no fields removed.
 * Clients pinned to /api/v1/orders are not affected.
 */
public record OrderResponseV2(
        Long id,
        String product,
        BigDecimal amount,
        String currency,
        BigDecimal amountWithTax,
        String status,
        Instant createdAt
) {

    private static final BigDecimal VAT = new BigDecimal("0.20");

    public static OrderResponseV2 from(Order order) {
        BigDecimal withTax = order.amount()
                .multiply(BigDecimal.ONE.add(VAT))
                .setScale(2, RoundingMode.HALF_UP);

        return new OrderResponseV2(
                order.id(),
                order.product(),
                order.amount(),
                "EUR",
                withTax,
                order.status(),
                Instant.now()
        );
    }
}
