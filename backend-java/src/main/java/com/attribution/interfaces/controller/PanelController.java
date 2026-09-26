package com.attribution.interfaces.controller;

import com.attribution.application.service.StockPanelService;
import com.attribution.interfaces.dto.StockPanelQuery;
import com.attribution.interfaces.dto.StockPanelResponse;
import com.attribution.interfaces.dto.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 股票面板控制_- 多表 JOIN 查询
 *
 * 与前端 stock-info/api.ts 对齐：
 * - 路径 /api/v1/stock-panel（同时兼容 trailing slash）
 * - query 参数 snake_case (page_size, with_pools, list_status 等)
 * - 响应 data.items / data.total / data.page / data.page_size
 */
@RestController
@RequestMapping("/api/v1/stock-panel")
@RequiredArgsConstructor
@Tag(name = "股票面板", description = "股票面板聚合查询")
public class PanelController {

    private final StockPanelService panelService;

    @GetMapping(value = {"", "/"})
    @Operation(summary = "查询股票面板")
    public ResponseEntity<ApiResponse<Map<String, Object>>> queryPanel(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String industry,
            @RequestParam(required = false) String market,
            @RequestParam(required = false) String exchange,
            @RequestParam(name = "is_hs", required = false) String isHs,
            @RequestParam(name = "list_status", required = false) String listStatus,
            @RequestParam(name = "exclude_st", required = false) Boolean excludeSt,
            @RequestParam(name = "min_total_mv", required = false) Double minTotalMv,
            @RequestParam(required = false) String sectorCode,
            @RequestParam(required = false) String sortBy,
            @RequestParam(defaultValue = "desc") String sortDir,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate tradeDate,
            @RequestParam(name = "with_indicators", defaultValue = "false") Boolean withIndicators,
            @RequestParam(name = "with_pools", defaultValue = "false") Boolean withPools,
            @RequestParam(name = "with_concepts", defaultValue = "false") Boolean withConcepts) {

        StockPanelQuery query = StockPanelQuery.builder()
            .page(page)
            .size(pageSize)
            .keyword(q)
            .industry(industry)
            .market(market)
            .exchange(exchange)
            .isHs(isHs)
            .listStatus(listStatus)
            .excludeSt(excludeSt)
            .minTotalMv(minTotalMv)
            .sectorCode(sectorCode)
            .sortBy(sortBy)
            .sortDir(sortDir)
            .tradeDate(tradeDate)
            .withIndicators(withIndicators)
            .withPools(withPools)
            .withConcepts(withConcepts)
            .build();

        StockPanelResponse resp = panelService.queryPanel(query);

        List<?> items = resp.getRows() != null ? resp.getRows() : List.of();

        Map<String, Object> data = new java.util.LinkedHashMap<>();
        data.put("total", resp.getTotal());
        data.put("page", resp.getPage());
        data.put("pageSize", resp.getSize());
        data.put("dataList", items);
        data.put("trade_date", resp.getTradeDate() != null ? resp.getTradeDate().toString() : null);
        return ResponseEntity.ok(ApiResponse.ok(data));
    }
}
