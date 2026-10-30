package com.attribution.market.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.market.service.DataBoardService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/stocks")
@RequiredArgsConstructor
public class StockAnalysisController {
    private final DataBoardService dataBoardService;

    @GetMapping("/{symbol}/analysis")
    public ApiResponse<?> analysis(
            @PathVariable String symbol, @RequestParam(defaultValue = "365") int days) {
        return ApiResponse.ok(dataBoardService.analysis(symbol, days));
    }
}
