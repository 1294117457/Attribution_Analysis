package com.attribution.infrastructure.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;

@Configuration
public class WebClientConfig {

    @Bean
    public WebClient tushareWebClient(TushareProperties properties) {
        return WebClient.builder()
            .baseUrl(properties.getBaseUrl())
            .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(50 * 1024 * 1024))
            .build();
    }

    @Bean
    public WebClient.Builder webClientBuilder() {
        return WebClient.builder()
            .codecs(configurer -> configurer.defaultCodecs().maxInMemorySize(50 * 1024 * 1024));
    }

    @Bean
    public Duration webClientTimeout(TushareProperties properties) {
        return Duration.ofMillis(properties.getTimeout());
    }
}
