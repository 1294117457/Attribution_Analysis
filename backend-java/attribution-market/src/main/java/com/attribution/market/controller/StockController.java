package com.attribution.market.controller;

import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.*;

import com.attribution.collector.client.CollectorService;
import com.attribution.common.response.ApiResponse;
import com.attribution.market.service.StockInfoService;

import lombok.RequiredArgsConstructor;

/**
 * 股票基础信息接口。
 *
 * <p>★ 基础信息表 {@code fundamental_stock_basic} 属采集库 raw_data，由 Collector 独占写入，
 * Java **只读**（规范：docs/规范文档/多库分工与数据源规范.md §2.1 铁律 3）。
 * 因此本 Controller **不提供** 新增 / 修改 / 删除接口——需要变更基础信息请走采集同步。
 */
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

    @PostMapping("/sync")
    public ApiResponse<?> sync(@RequestParam(defaultValue = "L") String list_status) {
        Map<String, Object> taskResult =
                collectorService.createTask(
                        "fundamental", "stock_basic", Map.of("list_status", list_status), "condition");
        return ApiResponse.created(taskResult);
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
