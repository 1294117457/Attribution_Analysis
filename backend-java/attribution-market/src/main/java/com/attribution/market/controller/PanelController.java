package com.attribution.market.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.market.dto.StockPanelQuery;
import com.attribution.market.service.StockInfoService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/stock-panel")
@RequiredArgsConstructor
public class PanelController {
    private final StockInfoService stockInfoService;

    @GetMapping("/")
    public ApiResponse<?> page(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String industry,
            @RequestParam(required = false) String market,
            @RequestParam(required = false) String exchange,
            @RequestParam(required = false) String is_hs,
            @RequestParam(defaultValue = "L") String list_status,
            @RequestParam(required = false) Boolean exclude_st,
            @RequestParam(required = false) Double min_total_mv,
            @RequestParam(required = false) Integer concept_id,
            @RequestParam(defaultValue = "false") boolean with_pools,
            @RequestParam(defaultValue = "false") boolean with_concepts,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int page_size) {
        StockPanelQuery query = new StockPanelQuery();
        query.setKeyword(q);
        query.setIndustry(industry);
        query.setMarket(market);
        query.setExchange(exchange);
        query.setIsHs(is_hs);
        query.setListStatus(list_status);
        query.setExcludeSt(exclude_st);
        query.setMinTotalMv(min_total_mv);
        query.setConceptId(concept_id);
        query.setWithPools(with_pools);
        query.setWithConcepts(with_concepts);
        query.setPage(Math.max(page, 1));
        query.setPageSize(Math.min(Math.max(page_size, 1), 500));
        return ApiResponse.ok(stockInfoService.page(query));
    }
}
