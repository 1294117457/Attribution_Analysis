package com.attribution.interfaces.controller;

import com.attribution.interfaces.dto.kline.KlineCollectRequest;
import com.attribution.interfaces.dto.kline.KlineCollectVO;
import com.attribution.interfaces.dto.kline.KlineDeleteRequest;
import com.attribution.interfaces.dto.kline.KlineQueryRequest;
import com.attribution.interfaces.dto.kline.KlineStatsVO;
import com.attribution.interfaces.dto.kline.KlineVO;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.interfaces.dto.response.PageVO;
import com.attribution.application.service.KlineService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/klines")
@RequiredArgsConstructor
@Tag(name = "K线", description = "日K线查询与采集")
public class KlineController {

    private final KlineService klineService;

    @GetMapping("/{symbol}")
    @Operation(summary = "查询K线（分页响应）")
    public ApiResponse<PageVO<KlineVO>> getKlines(
            @PathVariable String symbol,
            @RequestParam(name = "start_date", required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam(name = "end_date", required = false)
            @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate,
            @RequestParam(name = "limit", defaultValue = "365") @Min(1) @Max(3650) Integer limit,
            @RequestParam(name = "order_desc", defaultValue = "true") Boolean orderDesc,
            @RequestParam(name = "page", defaultValue = "1") @Min(1) Integer page,
            @RequestParam(name = "page_size", defaultValue = "1000") @Min(1) @Max(3650) Integer pageSize) {

        KlineQueryRequest req = KlineQueryRequest.builder()
                .symbol(symbol)
                .startDate(startDate)
                .endDate(endDate)
                .limit(limit)
                .orderDesc(orderDesc)
                .build();

        List<KlineVO> all = klineService.getKlines(req);

        // 支持分页（前端传 page/page_size）
        int total = all.size();
        int fromIndex = (page - 1) * pageSize;
        int toIndex = Math.min(fromIndex + pageSize, total);
        List<KlineVO> pageData = (fromIndex < total)
                ? all.subList(fromIndex, toIndex)
                : List.of();

        PageVO<KlineVO> pageVO = PageVO.of(total, page, pageSize, pageData);
        return ApiResponse.ok(pageVO);
    }

    @GetMapping("/{symbol}/stats")
    @Operation(summary = "K线统计")
    public ApiResponse<KlineStatsVO> getStats(@PathVariable String symbol) {
        return ApiResponse.ok(klineService.getStats(symbol));
    }

    @GetMapping("/{symbol}/{tradeDate}")
    @Operation(summary = "查询单条K线")
    public ApiResponse<KlineVO> getKlineByDate(
            @PathVariable String symbol,
            @PathVariable @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate tradeDate) {
        return ApiResponse.ok(klineService.getKlineByDate(symbol, tradeDate));
    }

    @PostMapping("/collect")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "采集K线")
    public ApiResponse<KlineCollectVO> collect(
            @Valid @RequestBody KlineCollectRequest request) {
        KlineCollectVO result = klineService.collect(request);
        return ApiResponse.created(result);
    }

    @PostMapping("/collect/batch")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "批量采集K线")
    public ApiResponse<Map<String, KlineCollectVO>> collectBatch(
            @RequestParam List<String> symbols,
            @RequestParam(defaultValue = "30") @Min(1) @Max(3650) Integer days) {
        return ApiResponse.created(klineService.collectBatch(symbols, days));
    }

    @DeleteMapping("/{symbol}")
    @Operation(summary = "删除全部K线")
    public ApiResponse<Void> deleteAll(@PathVariable String symbol) {
        KlineDeleteRequest req = KlineDeleteRequest.builder().symbol(symbol).build();
        klineService.deleteAll(req.getSymbol());
        return ApiResponse.ok(null, "删除成功");
    }

    @DeleteMapping("/{symbol}/{tradeDate}")
    @Operation(summary = "删除单条K线")
    public ApiResponse<Void> deleteByDate(
            @PathVariable String symbol,
            @PathVariable @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate tradeDate) {
        klineService.deleteByDate(symbol, tradeDate);
        return ApiResponse.ok(null, "删除成功");
    }
}
