package com.example.sampleapp.payment;

/**
 * @param transactionId null when payment failed or circuit is open.
 * @param status        AUTHORIZED | SETTLED | FAILED | CIRCUIT_OPEN
 */
public record PaymentResult(Long orderId, String transactionId, String status) {}
