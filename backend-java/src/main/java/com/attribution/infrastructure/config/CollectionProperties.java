package com.attribution.infrastructure.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "collection.task")
@Getter
@Setter
public class CollectionProperties {

    private int batchSize = 100;
    private int batchDelay = 1000;
    private int maxConcurrency = 50;
    private int defaultLookbackDays = 365;
}
