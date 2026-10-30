package com.attribution.market.controller;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.*;

import com.attribution.collector.client.CollectorService;
import com.attribution.common.response.ApiResponse;
import com.attribution.market.dto.KlineCollectRequest;
import com.attribution.market.dto.KlineQuery;
import com.attribution.market.service.KlineService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/klines")
@RequiredArgsConstructor
public class KlineController {
    private final KlineService klineService;
    private final CollectorService collectorService;

    @GetMapping("/{symbol}")
    public ApiResponse<?> list(
            @PathVariable String symbol,
            @RequestParam(required = false) String start_date,
            @RequestParam(required = false) String end_date,
            @RequestParam(defaultValue = "365") int limit,
            @RequestParam(defaultValue = "true") boolean order_desc) {
        KlineQuery query = new KlineQuery();
        query.setStartDate(start_date);
        query.setEndDate(end_date);
        query.setLimit(limit);
        query.setOrderDesc(order_desc);
        return ApiResponse.ok(klineService.list(symbol, query));
    }

    @GetMapping("/{symbol}/stats")
    public ApiResponse<?> stats(@PathVariable String symbol) {
        return ApiResponse.ok(klineService.stats(symbol));
    }

    @GetMapping("/{symbol}/{trade_date}")
    public ApiResponse<?> one(@PathVariable String symbol, @PathVariable String trade_date) {
        return ApiResponse.ok(klineService.one(symbol, trade_date));
    }

    /** 采集单只股票 K 线：转后台任务，立即返回 task_id（前端轮询 /api/collect/tasks/{id}） */
    @PostMapping("/collect")
    public ApiResponse<?> collect(@Valid @RequestBody KlineCollectRequest request) {
        Map<String, Object> params = new LinkedHashMap<>();
        params.put("symbols", List.of(request.getSymbol()));
        if (request.getDays() != null) params.put("days", request.getDays());
        if (request.getStartDate() != null) params.put("start_date", request.getStartDate());
        if (request.getEndDate() != null) params.put("end_date", request.getEndDate());
        return ApiResponse.created(collectorService.createTask("tech", "daily_kline", params, "condition"));
    }

    /** 批量采集 K 线：转后台任务，立即返回 task_id */
    @PostMapping("/collect/batch")
    public ApiResponse<?> batch(
            @RequestParam List<String> symbols, @RequestParam(defaultValue = "30") int days) {
        return ApiResponse.created(
                collectorService.createTask(
                        "tech", "daily_kline", Map.of("symbols", symbols, "days", days), "condition"));
    }

    @DeleteMapping("/{symbol}")
    public ApiResponse<?> deleteAll(@PathVariable String symbol) {
        return ApiResponse.ok(klineService.deleteAll(symbol));
    }

    @DeleteMapping("/{symbol}/{trade_date}")
    public ApiResponse<?> deleteOne(@PathVariable String symbol, @PathVariable String trade_date) {
        return ApiResponse.ok(klineService.deleteOne(symbol, trade_date));
    }
}
