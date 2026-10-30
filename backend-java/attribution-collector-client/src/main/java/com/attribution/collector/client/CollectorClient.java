package com.attribution.collector.client;

import java.util.Map;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

/** Collector Feign：只透传任务式采集 + 目录 + 实时查询（同步 collect 已下线）。 */
@FeignClient(
        name = "collector",
        url = "${collector.base-url:http://localhost:8001}",
        fallback = CollectorFallback.class)
public interface CollectorClient {
    @GetMapping("/api/collect/services")
    Map<String, Object> services();

    @GetMapping("/api/collect/query/{name}")
    Map<String, Object> query(@PathVariable("name") String name, @RequestParam("params") String paramsJson);

    @PostMapping("/api/collect/tasks/{facet}/{name}")
    Map<String, Object> createTask(
            @PathVariable("facet") String facet,
            @PathVariable("name") String name,
            @RequestBody Map<String, Object> body);

    @GetMapping("/api/collect/tasks/{taskId}")
    Map<String, Object> taskState(@PathVariable("taskId") String taskId);

    @GetMapping("/api/collect/tasks")
    Map<String, Object> taskList(@RequestParam(value = "limit", required = false) Integer limit);

    @PostMapping("/api/collect/tasks/{taskId}/cancel")
    Map<String, Object> cancelTask(@PathVariable("taskId") String taskId);
}
