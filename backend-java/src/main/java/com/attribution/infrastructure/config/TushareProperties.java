package com.attribution.infrastructure.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "tushare")
@Getter
@Setter
public class TushareProperties {

    private String token = "";
    private String baseUrl = "http://api.tushare.pro";
    private int timeout = 30_000;
    private int maxRetries = 3;
    private int rateLimit = 33;
}
