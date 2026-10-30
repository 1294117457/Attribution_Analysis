package com.attribution.concept.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.concept.dto.ConceptQuery;
import com.attribution.concept.service.ConceptService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/concepts")
@RequiredArgsConstructor
public class ConceptQueryController {
    private final ConceptService conceptService;

    @GetMapping("/")
    public ApiResponse<?> list(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) Boolean is_active,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int page_size) {
        ConceptQuery query = new ConceptQuery();
        query.setKeyword(q);
        query.setIsActive(is_active);
        query.setPage(Math.max(page, 1));
        query.setPageSize(Math.min(Math.max(page_size, 1), 100));
        return ApiResponse.ok(conceptService.list(query));
    }

    @GetMapping("/by-symbol/{symbol}")
    public ApiResponse<?> by(@PathVariable String symbol) {
        return ApiResponse.ok(conceptService.bySymbol(symbol));
    }

    @GetMapping("/live-by-symbol/{symbol}")
    public ApiResponse<?> live(@PathVariable String symbol) {
        return ApiResponse.ok(conceptService.liveBySymbol(symbol));
    }

    @GetMapping("/tab-by-symbol/{symbol}")
    public ApiResponse<?> tab(
            @PathVariable String symbol,
            @RequestParam(required = false) String stock_name,
            @RequestParam(defaultValue = "false") boolean merge_live) {
        return ApiResponse.ok(conceptService.tab(symbol, stock_name, merge_live));
    }

    @GetMapping("/sync/status")
    public ApiResponse<?> status() {
        return ApiResponse.ok(conceptService.syncStatus());
    }

    @GetMapping("/{name}")
    public ApiResponse<?> detail(@PathVariable String name) {
        return ApiResponse.ok(conceptService.detail(name));
    }

    @GetMapping("/{name}/index-th")
    public ApiResponse<?> idx(
            @PathVariable String name,
            @RequestParam(required = false) String start_date,
            @RequestParam(required = false) String end_date,
            @RequestParam(defaultValue = "500") int limit) {
        return ApiResponse.ok(conceptService.indexKline(name, start_date, end_date, Math.min(limit, 2000)));
    }
}
