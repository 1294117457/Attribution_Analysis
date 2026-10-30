package com.attribution.market.controller;

import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.*;

import com.attribution.collector.client.CollectorService;
import com.attribution.common.response.ApiResponse;
import com.attribution.market.dto.StockUpdateRequest;
import com.attribution.market.service.StockInfoService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/stocks")
@RequiredArgsConstructor
public class StockController {
    private final StockInfoService stockInfoService;
    private final CollectorService collectorService;

    @GetMapping("/meta")
    public ApiResponse<?> meta() {
        return ApiResponse.ok(stockInfoService.meta());
    }

    @GetMapping("/{symbol}")
    public ApiResponse<?> one(@PathVariable String symbol) {
        return ApiResponse.ok(stockInfoService.get(symbol));
    }

    @PostMapping("/")
    public ApiResponse<?> upsert(
            @RequestParam String symbol,
            @RequestParam String name,
            @RequestParam(required = false) String industry,
            @RequestParam(required = false) String market) {
        return ApiResponse.created(stockInfoService.upsert(symbol, name, industry, market));
    }

    @PostMapping("/sync")
    public ApiResponse<?> sync(@RequestParam(defaultValue = "L") String list_status) {
        Map<String, Object> taskResult =
                collectorService.createTask(
                        "fundamental", "stock_basic", Map.of("list_status", list_status), "condition");
        return ApiResponse.created(taskResult);
    }

    @PatchMapping("/{symbol}")
    public ApiResponse<?> patch(
            @PathVariable String symbol, @Valid @RequestBody StockUpdateRequest request) {
        return ApiResponse.ok(stockInfoService.patch(symbol, request));
    }

    @DeleteMapping("/{symbol}")
    public ApiResponse<?> delete(@PathVariable String symbol) {
        stockInfoService.delete(symbol);
        return ApiResponse.ok(null);
    }

    @PostMapping("/sync-daily-basic")
    public ApiResponse<?> syncDailyBasic(
            @RequestParam(required = false) String trade_date, @RequestParam(defaultValue = "1") int days) {
        if (trade_date == null)
            return ApiResponse.ok(
                    Map.of(
                            "synced_count", 0,
                            "dates", List.of(),
                            "message", "请提供 trade_date（YYYYMMDD）"));
        Map<String, Object> syncResult =
                collectorService.createTask(
                        "fundamental", "daily_basic", Map.of("trade_date", trade_date, "days", days), "condition");
        return ApiResponse.ok(syncResult);
    }
}
