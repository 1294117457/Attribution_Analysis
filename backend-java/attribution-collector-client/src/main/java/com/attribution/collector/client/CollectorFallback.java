package com.attribution.collector.client;

import java.util.Map;

import org.springframework.stereotype.Component;

@Component
public class CollectorFallback implements CollectorClient {
    private static Map<String, Object> unavailable() {
        Map<String, Object> fallback = new java.util.LinkedHashMap<>();
        fallback.put("code", 503);
        fallback.put("message", "collector unavailable");
        fallback.put("data", null);
        return fallback;
    }

    public Map<String, Object> services() {
        return unavailable();
    }

    public Map<String, Object> query(String serviceName, String params) {
        return unavailable();
    }

    public Map<String, Object> createTask(String facet, String serviceName, Map<String, Object> body) {
        return unavailable();
    }

    public Map<String, Object> taskState(String taskId) {
        return unavailable();
    }

    public Map<String, Object> taskList(Integer limit) {
        return unavailable();
    }

    public Map<String, Object> cancelTask(String taskId) {
        return unavailable();
    }
}
