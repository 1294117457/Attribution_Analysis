package com.attribution.interfaces.controller;

import com.attribution.infrastructure.adapter.collector.pytdx.PytdxMinuteKlineCollector;
import com.attribution.interfaces.dto.kline.MinuteKlineVO;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.interfaces.dto.response.ErrorCode;
import com.attribution.interfaces.dto.response.PageVO;
import com.attribution.infrastructure.exception.BusinessException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 分钟 K 线 API（实时透传，不入库）。
 *
 * <p>采集路径：东方财富公开接口（首选）→ 新浪公开接口（兜底）→ Tushare stk_mins（需付费权限）。
 */
@RestController
@RequestMapping("/api/v1/minute-klines")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "分钟K线", description = "实时分钟 K 线（透传）")
public class MinuteKlineController {

    private final PytdxMinuteKlineCollector collector;

    @GetMapping("/{symbol}")
    @Operation(summary = "实时获取分钟 K 线")
    public ApiResponse<PageVO<MinuteKlineVO>> getMinuteKlines(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "5min") String interval,
            @RequestParam(defaultValue = "200") Integer count) {

        try {
            List<MinuteKlineVO> items = collector.fetchMinuteKlines(symbol, interval, count).stream()
                    .map(this::toVO)
                    .collect(Collectors.toList());
            // 分页结构（与日K端一致）：分钟 K 线常一次性拉 200 条，不再二次分页
            PageVO<MinuteKlineVO> pageVO = PageVO.of(items.size(), 1, items.size(), items);
            return ApiResponse.ok(pageVO);
        } catch (BusinessException e) {
            log.warn("分 K 拉取失败: {}", e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("分 K 拉取异常: {}", symbol, e);
            throw new BusinessException(
                    "minute_kline",
                    "EAST_MONEY_API_ERROR",
                    "分 K 拉取失败: " + e.getMessage(),
                    HttpStatus.BAD_GATEWAY);
        }
    }

    private MinuteKlineVO toVO(java.util.Map<String, Object> m) {
        return MinuteKlineVO.builder()
                .datetime(safeStr(m.get("datetime")))
                .interval(safeStr(m.get("interval")))
                .open(safeDouble(m.get("open")))
                .high(safeDouble(m.get("high")))
                .low(safeDouble(m.get("low")))
                .close(safeDouble(m.get("close")))
                .volume(safeLong(m.get("volume")))
                .amount(safeDouble(m.get("amount")))
                .build();
    }

    private String safeStr(Object v) {
        return v == null ? null : v.toString();
    }

    private Double safeDouble(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(v.toString());
        } catch (Exception e) {
            return null;
        }
    }

    private Long safeLong(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(v.toString());
        } catch (Exception e) {
            return null;
        }
    }
}
