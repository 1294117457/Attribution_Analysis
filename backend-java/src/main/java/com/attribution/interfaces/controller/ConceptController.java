package com.attribution.interfaces.controller;

import com.attribution.interfaces.dto.ConceptBriefVO;
import com.attribution.interfaces.dto.ConceptDetailVO;
import com.attribution.interfaces.dto.ConceptSyncStatusVO;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.application.service.ConceptService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/concepts")
@RequiredArgsConstructor
@Tag(name = "概念", description = "概念板块")
public class ConceptController {

    private final ConceptService conceptService;

    @GetMapping
    @Operation(summary = "概念列表")
    public ResponseEntity<ApiResponse<List<ConceptBriefVO>>> list(
            @RequestParam(required = false) String source) {
        return ResponseEntity.ok(ApiResponse.ok(conceptService.getAllConcepts(source)));
    }

    @GetMapping("/{code}")
    @Operation(summary = "概念详情")
    public ResponseEntity<ApiResponse<ConceptDetailVO>> get(@PathVariable String code) {
        return ResponseEntity.ok(ApiResponse.ok(conceptService.getConceptDetail(code)));
    }

    @GetMapping("/by-symbol/{symbol}")
    @Operation(summary = "股票所属概念")
    public ResponseEntity<ApiResponse<List<ConceptBriefVO>>> getBySymbol(@PathVariable String symbol) {
        return ResponseEntity.ok(ApiResponse.ok(conceptService.getStockConcepts(symbol)));
    }

    @GetMapping("/sync/status")
    @Operation(summary = "同步状")
    public ResponseEntity<ApiResponse<ConceptSyncStatusVO>> getSyncStatus(
            @RequestParam(defaultValue = "tushare") String source) {
        return ResponseEntity.ok(ApiResponse.ok(conceptService.getSyncStatus(source)));
    }
}
