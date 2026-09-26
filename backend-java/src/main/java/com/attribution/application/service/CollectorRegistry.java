package com.attribution.application.service;

import com.attribution.infrastructure.adapter.collector.Collector;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

@Component
@Slf4j
public class CollectorRegistry {

    private final Map<String, Collector> collectors = new HashMap<>();

    public void register(String key, Collector collector) {
        collectors.put(key, collector);
        log.info("注册采集_ {} -> {}", key, collector.name());
    }

    public Collector getKlineCollector() {
        Collector c = collectors.get("kline");
        if (c == null) {
            throw new IllegalStateException("K线采集器未注册，请检_setup_collectors()");
        }
        return c;
    }

    public Collector get(String key) {
        Collector c = collectors.get(key);
        if (c == null) {
            throw new IllegalStateException("采集器未注册: " + key);
        }
        return c;
    }

    public boolean has(String key) {
        return collectors.containsKey(key);
    }
}
