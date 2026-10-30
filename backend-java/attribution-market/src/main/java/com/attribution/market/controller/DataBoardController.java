package com.attribution.market.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.market.dto.StockListQuery;
import com.attribution.market.service.DataBoardService;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/data-board")
@RequiredArgsConstructor
public class DataBoardController {
    private final DataBoardService dataBoardService;

    @GetMapping("/tech/kline/{symbol}")
    public ApiResponse<?> techKline(
            @PathVariable String symbol,
            @RequestParam(required = false) String start_date,
            @RequestParam(required = false) String end_date,
            @RequestParam(defaultValue = "250") int limit) {
        return ApiResponse.ok(dataBoardService.techKline(symbol, limit));
    }

    @GetMapping("/tech/adj-factor/{symbol}")
    public ApiResponse<?> adjFactor(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.adjFactor(symbol));
    }

    @GetMapping("/tech/suspend/{symbol}")
    public ApiResponse<?> suspend(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.suspend(symbol));
    }

    @GetMapping("/tech/name-change/{symbol}")
    public ApiResponse<?> nameChange(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.nameChange(symbol));
    }

    @GetMapping("/capital/moneyflow/{symbol}")
    public ApiResponse<?> moneyflow(@PathVariable String symbol, @RequestParam(defaultValue = "60") int days) {
        return ApiResponse.ok(dataBoardService.moneyflow(symbol, days));
    }

    @GetMapping("/capital/margin/{symbol}")
    public ApiResponse<?> margin(@PathVariable String symbol, @RequestParam(defaultValue = "60") int days) {
        return ApiResponse.ok(dataBoardService.margin(symbol, days));
    }

    @GetMapping("/capital/top-list/{symbol}")
    public ApiResponse<?> topList(@PathVariable String symbol, @RequestParam(defaultValue = "90") int days) {
        return ApiResponse.ok(dataBoardService.topList(symbol, days));
    }

    @GetMapping("/capital/top-inst/{symbol}")
    public ApiResponse<?> topInst(@PathVariable String symbol, @RequestParam(defaultValue = "90") int days) {
        return ApiResponse.ok(dataBoardService.topInst(symbol, days));
    }

    @GetMapping("/capital/block-trade/{symbol}")
    public ApiResponse<?> blockTrade(@PathVariable String symbol, @RequestParam(defaultValue = "180") int days) {
        return ApiResponse.ok(dataBoardService.blockTrade(symbol, days));
    }

    @GetMapping("/capital/holder-num/{symbol}")
    public ApiResponse<?> holderNum(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.holderNum(symbol));
    }

    @GetMapping("/fundamental/stock/{symbol}")
    public ApiResponse<?> fundamentalStock(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.stockInfo(symbol));
    }

    @GetMapping("/fundamental/daily-basic/{symbol}")
    public ApiResponse<?> dailyBasic(@PathVariable String symbol, @RequestParam(defaultValue = "60") int days) {
        return ApiResponse.ok(dataBoardService.dailyBasic(symbol, days));
    }

    @GetMapping("/fundamental/fin-report/{symbol}")
    public ApiResponse<?> finReport(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.finReport(symbol));
    }

    @GetMapping("/fundamental/top10-holders/{symbol}")
    public ApiResponse<?> top10Holders(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.top10Holders(symbol));
    }

    @GetMapping("/fundamental/top10-float/{symbol}")
    public ApiResponse<?> top10Float(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.top10Float(symbol));
    }

    @GetMapping("/fundamental/dividend/{symbol}")
    public ApiResponse<?> dividend(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.dividend(symbol));
    }

    @GetMapping("/overview/{symbol}")
    public ApiResponse<?> overview(@PathVariable String symbol) {
        return ApiResponse.ok(dataBoardService.overview(symbol));
    }

    @GetMapping("/stock-list")
    public ApiResponse<?> stockList(
            @RequestParam(required = false) String q,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "50") int page_size,
            @RequestParam(defaultValue = "L") String list_status) {
        StockListQuery query = new StockListQuery();
        query.setKeyword(q);
        query.setPage(Math.max(page, 1));
        query.setPageSize(Math.min(Math.max(page_size, 1), 200));
        query.setListStatus(list_status);
        return ApiResponse.ok(dataBoardService.stockList(query));
    }

    @GetMapping("/stock-list-all")
    public ApiResponse<?> stockListAll() {
        return ApiResponse.ok(dataBoardService.stockListAll());
    }
}
