package com.example.sampleapp.payment;

import io.micrometer.observation.annotation.Observed;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.CircuitBreaker;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;

/**
 * Demonstrates two resilience patterns with Spring Retry:
 *
 * 1. @Retryable — authorize(): transient failures are retried up to 3 times
 *    with exponential backoff (100ms → 200ms → 400ms, capped at 500ms).
 *    The @Observed span covers the full attempt sequence.
 *
 * 2. @CircuitBreaker — settle(): after repeated failures within the openTimeout
 *    window, the circuit opens and calls are short-circuited immediately to the
 *    @Recover fallback for resetTimeout milliseconds.
 *
 * Both patterns are visible in Tempo: look for payment.* spans and observe
 * the duration difference between retried vs circuit-open calls.
 */
@Service
public class PaymentService {

    private static final Logger log = LoggerFactory.getLogger(PaymentService.class);

    private final ExternalPaymentGateway gateway;

    public PaymentService(ExternalPaymentGateway gateway) {
        this.gateway = gateway;
    }

    // -------------------------------------------------------------------------
    // Authorize — retried on transient failures
    // -------------------------------------------------------------------------

    @Observed(name = "payment.authorize", contextualName = "authorizing-payment")
    @Retryable(
            retryFor = PaymentGatewayException.class,
            maxAttempts = 3,
            backoff = @Backoff(delay = 100, multiplier = 2, maxDelay = 500)
    )
    public PaymentResult authorize(Long orderId, BigDecimal amount) {
        log.info("Attempting payment authorization — orderId={} amount={}", orderId, amount);
        return gateway.call("authorize", orderId);
    }

    @Recover
    public PaymentResult authorizeRecover(PaymentGatewayException ex, Long orderId, BigDecimal amount) {
        log.warn("Payment authorization exhausted all retries — orderId={} reason={}", orderId, ex.getMessage());
        return new PaymentResult(orderId, null, "FAILED");
    }

    // -------------------------------------------------------------------------
    // Settle — protected by circuit breaker
    // openTimeout:  5 000ms — window to reach maxAttempts before opening circuit
    // resetTimeout: 20 000ms — circuit stays OPEN before moving to HALF_OPEN
    // -------------------------------------------------------------------------

    @Observed(name = "payment.settle", contextualName = "settling-payment")
    @CircuitBreaker(
            include = PaymentGatewayException.class,
            openTimeout = 5_000L,
            resetTimeout = 20_000L
    )
    public PaymentResult settle(Long orderId) {
        log.info("Attempting payment settlement — orderId={}", orderId);
        return gateway.call("settle", orderId);
    }

    @Recover
    public PaymentResult settleRecover(PaymentGatewayException ex, Long orderId) {
        log.error("Circuit breaker triggered — settlement unavailable — orderId={} reason={}", orderId, ex.getMessage());
        return new PaymentResult(orderId, null, "CIRCUIT_OPEN");
    }
}
