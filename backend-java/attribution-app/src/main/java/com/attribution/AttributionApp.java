package com.attribution;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication
@MapperScan({
    "com.attribution.market.mapper",
    "com.attribution.concept.mapper",
    "com.attribution.user.mapper",
    "com.attribution.auth.mapper"
})
@EnableFeignClients("com.attribution.collector.client")
public class AttributionApp {
    public static void main(String[] a) {
        SpringApplication.run(AttributionApp.class, a);
    }
}
