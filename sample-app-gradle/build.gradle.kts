plugins {
    java
    id("org.springframework.boot") version "4.0.3"
    id("io.spring.dependency-management") version "1.1.7"
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

repositories {
    mavenCentral()
}

dependencies {

    // =========================================================================
    // Core — always included
    // =========================================================================
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-opentelemetry")
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    // Renamed from spring-boot-starter-aop in Spring Boot 4
    implementation("org.springframework.boot:spring-boot-starter-aspectj")
    // OTel Logback Appender — not managed by Spring Boot BOM
    implementation("io.opentelemetry.instrumentation:opentelemetry-logback-appender-1.0:2.26.0-alpha")
    // Spring Retry — @Retryable + @CircuitBreaker with exponential backoff
    implementation("org.springframework.retry:spring-retry:2.0.12")

    // =========================================================================
    // Test
    // =========================================================================
    testImplementation("org.springframework.boot:spring-boot-starter-actuator-test")
    testImplementation("org.springframework.boot:spring-boot-starter-opentelemetry-test")
    testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")
}
