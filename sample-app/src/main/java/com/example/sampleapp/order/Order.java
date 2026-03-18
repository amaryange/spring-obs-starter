package com.example.sampleapp.order;

import java.math.BigDecimal;

public record Order(Long id, String product, BigDecimal amount, String status) {}
