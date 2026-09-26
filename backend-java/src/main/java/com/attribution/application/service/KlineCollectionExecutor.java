package com.attribution.application.service;

import com.attribution.infrastructure.adapter.collector.Collector;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class KlineCollectionExecutor {

    private final CollectorRegistry collectorRegistry;

    public void collectOne(String symbol, int days) {
        Collector collector = collectorRegistry.getKlineCollector();
        collector.collect(symbol, days);
    }
}
