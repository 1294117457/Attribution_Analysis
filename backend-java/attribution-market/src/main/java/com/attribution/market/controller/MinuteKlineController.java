package com.attribution.market.controller;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.*;

import com.attribution.collector.client.CollectorService;
import com.attribution.common.response.ApiResponse;
import com.attribution.market.vo.MinuteKlineBarVO;
import com.attribution.market.vo.MinuteKlineVO;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/minute-klines")
@RequiredArgsConstructor
public class MinuteKlineController {
    private final CollectorService collectorService;

    static final Map<String, String> INTERVAL_ALIAS =
            Map.of("1", "1min", "5", "5min", "15", "15min", "30", "30min", "60", "60min");

    @GetMapping("/{symbol}")
    public ApiResponse<?> get(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "5min") String interval,
            @RequestParam(defaultValue = "1") int days) {
        String resolvedInterval =
                INTERVAL_ALIAS.getOrDefault(String.valueOf(interval).trim(), String.valueOf(interval));
        Object data =
                collectorService.query(
                        "minute_kline", Map.of("symbol", symbol, "interval", resolvedInterval, "days", days));
        if (!(data instanceof List<?> rawList)) return ApiResponse.ok(data);

        List<MinuteKlineBarVO> bars = new ArrayList<>();
        for (Object rawItem : rawList) {
            if (!(rawItem instanceof Map<?, ?> rawMap)) continue;
            MinuteKlineBarVO barVO = new MinuteKlineBarVO();
            Object datetime = rawMap.get("dt");
            if (datetime == null) datetime = rawMap.get("datetime");
            barVO.setDatetime(datetime == null ? null : String.valueOf(datetime));
            Object barInterval = rawMap.get("interval");
            barVO.setInterval(barInterval != null ? String.valueOf(barInterval) : resolvedInterval);
            barVO.setOpen(numOf(rawMap.get("open")));
            barVO.setHigh(numOf(rawMap.get("high")));
            barVO.setLow(numOf(rawMap.get("low")));
            barVO.setClose(numOf(rawMap.get("close")));
            barVO.setVolume(numOf(rawMap.get("volume")));
            barVO.setAmount(numOf(rawMap.get("amount")));
            bars.add(barVO);
        }

        // 分钟 K 为实时透传，非分页接口：直接返回列表 + 缓存标记
        MinuteKlineVO result = new MinuteKlineVO();
        result.setSymbol(symbol);
        result.setInterval(resolvedInterval);
        result.setBars(bars);
        result.setCached(false);
        result.setFetchedAt(null);
        return ApiResponse.ok(result);
    }

    private static java.math.BigDecimal numOf(Object value) {
        if (value == null) return null;
        if (value instanceof java.math.BigDecimal decimal) return decimal;
        if (value instanceof Number number) return java.math.BigDecimal.valueOf(number.doubleValue());
        try {
            return new java.math.BigDecimal(String.valueOf(value));
        } catch (Exception e) {
            return null;
        }
    }
}
