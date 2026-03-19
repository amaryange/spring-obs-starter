package com.example.sampleapp.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.retry.annotation.EnableRetry;

/**
 * Activates Spring Retry AOP proxies for @Retryable and @CircuitBreaker.
 * Without @EnableRetry, annotations are present but have no effect at runtime.
 */
@Configuration
@EnableRetry
public class ResilienceConfig {
}
