package com.example.sampleapp.payment;

import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;

/**
 * Demo endpoints for resilience patterns.
 *
 * GET /api/v1/payment/authorize/{orderId}
 *   — triggers @Retryable: expect 2 failures then success (ExternalPaymentGateway pattern).
 *     Call repeatedly to see the counter advance and circuit eventually open.
 *
 * GET /api/v1/payment/settle/{orderId}
 *   — triggers @CircuitBreaker: after sustained failures, returns CIRCUIT_OPEN immediately.
 *     Circuit resets after 20s.
 */
@RestController
@RequestMapping("/api/v1/payment")
public class PaymentController {

    private final PaymentService paymentService;

    public PaymentController(PaymentService paymentService) {
        this.paymentService = paymentService;
    }

    @GetMapping("/authorize/{orderId}")
    public PaymentResult authorize(@PathVariable Long orderId) {
        return paymentService.authorize(orderId, new BigDecimal("100.00"));
    }

    @GetMapping("/settle/{orderId}")
    public PaymentResult settle(@PathVariable Long orderId) {
        return paymentService.settle(orderId);
    }
}
