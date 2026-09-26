package com.attribution.interfaces.controller;

import com.attribution.interfaces.dto.StockDetailVO;
import com.attribution.interfaces.dto.StockFinanceSnapshotVO;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.application.service.StockService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/stocks")
@RequiredArgsConstructor
@Tag(name = "股票", description = "股票信息与分")
public class StockController {

    private final StockService stockService;

    @GetMapping(value = {"", "/"})
    @Operation(summary = "股票列表（轻量版 — Dashboard 用）")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listStocks(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(name = "page_size", defaultValue = "8") int pageSize,
            @RequestParam(required = false) String industry,
            @RequestParam(required = false) String market) {

        org.springframework.data.domain.Page<com.attribution.domain.entity.StockInfoEntity> result =
            stockService.listStocks(page, pageSize, industry, market);

        List<Map<String, Object>> items = result.getContent().stream()
            .map(stock -> {
                Map<String, Object> m = new java.util.LinkedHashMap<>();
                m.put("symbol", stock.getSymbol());
                m.put("ts_code", stock.getTsCode());
                m.put("name", stock.getName());
                m.put("area", stock.getArea());
                m.put("industry", stock.getIndustry());
                m.put("market", stock.getMarket());
                m.put("exchange", stock.getExchange());
                m.put("list_date", stock.getListDate());
                m.put("list_status", stock.getListStatus());
                m.put("is_hs", stock.getIsHs());
                return m;
            })
            .toList();

        Map<String, Object> data = new java.util.LinkedHashMap<>();
        data.put("total", result.getTotalElements());
        data.put("page", page);
        data.put("pageSize", pageSize);
        data.put("dataList", items);
        return ResponseEntity.ok(ApiResponse.ok(data));
    }

    @GetMapping("/{symbol}")
    @Operation(summary = "股票详情")
    public ResponseEntity<ApiResponse<StockDetailVO>> getStock(@PathVariable String symbol) {
        return ResponseEntity.ok(ApiResponse.ok(stockService.getStockDetail(symbol)));
    }

    @GetMapping("/{symbol}/finance")
    @Operation(summary = "股票财务摘要")
    public ResponseEntity<ApiResponse<StockFinanceSnapshotVO>> getFinance(@PathVariable String symbol) {
        return ResponseEntity.ok(ApiResponse.ok(stockService.getFinanceSnapshot(symbol)));
    }
    @GetMapping("/meta")
    @Operation(summary = "股票枚举值（行业 / 市场 / 交易所）")
    public ResponseEntity<ApiResponse<com.attribution.interfaces.dto.StockMetaVO>> getMeta() {
        return ResponseEntity.ok(ApiResponse.ok(stockService.getMeta()));
    }
}
