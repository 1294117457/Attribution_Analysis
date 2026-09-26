package com.attribution;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.scheduling.annotation.EnableAsync;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.info.Info;

@SpringBootApplication
@EnableJpaAuditing
@EnableAsync
@EntityScan(basePackages = "com.attribution.domain.entity")
@EnableJpaRepositories(basePackages = "com.attribution.domain.repository")
@OpenAPIDefinition(
    info = @Info(
        title = "智能金融数据归因分析平台",
        description = "Java 21 + Spring Boot 3.3 重构版",
        version = "3.0.0"
    )
)
public class AttributionApplication {

    public static void main(String[] args) {
        SpringApplication.run(AttributionApplication.class, args);
    }
}
