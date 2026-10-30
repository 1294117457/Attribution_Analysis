package com.attribution.concept.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.concept.dto.ConceptBoardQuery;
import com.attribution.concept.dto.ConceptKlineQuery;
import com.attribution.concept.dto.ConceptMemberQuery;
import com.attribution.concept.service.ConceptService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/concepts")
@RequiredArgsConstructor
public class ConceptBoardController {
    private final ConceptService conceptService;

    @GetMapping("/concept-board")
    public ApiResponse<?> board(
            @RequestParam(defaultValue = "all") String type_filter,
            @RequestParam(defaultValue = "pct_change") String sort_by,
            @RequestParam(defaultValue = "desc") String order,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int page_size) {
        ConceptBoardQuery query = new ConceptBoardQuery();
        query.setTypeFilter(type_filter);
        query.setSortBy(sort_by);
        query.setSortOrder(order);
        query.setPage(Math.max(page, 1));
        query.setPageSize(Math.min(Math.max(page_size, 1), 500));
        return ApiResponse.ok(conceptService.board(query));
    }

    @GetMapping("/concept-board/members")
    public ApiResponse<?> members(
            @RequestParam int concept_id,
            @RequestParam(defaultValue = "pct_change") String sort_by,
            @RequestParam(defaultValue = "desc") String order,
            @RequestParam(defaultValue = "true") boolean with_pools,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int page_size) {
        ConceptMemberQuery query = new ConceptMemberQuery();
        query.setConceptId(concept_id);
        query.setSortBy(sort_by);
        query.setSortOrder(order);
        query.setWithPools(with_pools);
        query.setPage(Math.max(page, 1));
        query.setPageSize(Math.min(Math.max(page_size, 1), 200));
        return ApiResponse.ok(conceptService.members(query));
    }

    @GetMapping("/{index_code}/kline")
    public ApiResponse<?> k(
            @PathVariable String index_code,
            @RequestParam(defaultValue = "250") int days,
            @RequestParam(required = false) String start_date,
            @RequestParam(required = false) String end_date) {
        ConceptKlineQuery query = new ConceptKlineQuery();
        query.setDays(Math.min(days, 1500));
        query.setStartDate(start_date);
        query.setEndDate(end_date);
        return ApiResponse.ok(conceptService.conceptKline(index_code, query));
    }
}
