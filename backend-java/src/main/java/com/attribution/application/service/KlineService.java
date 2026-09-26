package com.attribution.application.service;

import com.attribution.infrastructure.adapter.collector.Collector;
import com.attribution.interfaces.dto.kline.KlineCollectRequest;
import com.attribution.interfaces.dto.kline.KlineCollectVO;
import com.attribution.interfaces.dto.kline.KlineQueryRequest;
import com.attribution.interfaces.dto.kline.KlineStatsVO;
import com.attribution.interfaces.dto.kline.KlineVO;
import com.attribution.infrastructure.exception.BusinessException;
import org.springframework.http.HttpStatus;
import com.attribution.domain.repository.TechKlineDailyRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class KlineService {

    private final TechKlineDailyRepository klineRepository;
    private final CollectorRegistry collectorRegistry;

    @Transactional(readOnly = true)
    public List<KlineVO> getKlines(KlineQueryRequest request) {
        if (Boolean.TRUE.equals(request.getOrderDesc())) {
            List<com.attribution.domain.entity.TechKlineDailyEntity> entities;
            if (request.getStartDate() != null && request.getEndDate() != null) {
                entities = klineRepository
                    .findBySymbolAndDateBetweenOrderByDateDesc(
                        request.getSymbol(),
                        request.getStartDate(),
                        request.getEndDate()
                    );
            } else {
                entities = klineRepository.findBySymbolOrderByDateDesc(request.getSymbol());
            }
            int limit = request.getLimit() != null ? request.getLimit() : entities.size();
            return entities.stream()
                .limit(limit)
                .map(KlineVO::fromEntity)
                .toList();
        } else {
            return getKlinesAsc(request);
        }
    }

    private List<KlineVO> getKlinesAsc(KlineQueryRequest request) {
        List<com.attribution.domain.entity.TechKlineDailyEntity> entities;
        if (request.getStartDate() != null && request.getEndDate() != null) {
            entities = klineRepository
                .findBySymbolAndDateBetweenOrderByDateAsc(
                    request.getSymbol(),
                    request.getStartDate(),
                    request.getEndDate()
                );
        } else {
            entities = klineRepository.findBySymbolOrderByDateDesc(request.getSymbol());
            java.util.Collections.reverse(entities);
        }
        int limit = request.getLimit() != null ? request.getLimit() : entities.size();
        return entities.stream()
            .limit(limit)
            .map(KlineVO::fromEntity)
            .toList();
    }

    @Transactional(readOnly = true)
    public KlineVO getKlineByDate(String symbol, LocalDate tradeDate) {
        var entity = klineRepository.findBySymbolAndDate(symbol, tradeDate)
            .orElseThrow(() -> new BusinessException("kline", "KLINE_NOT_FOUND",
                "K线数据不存在: " + symbol + " @ " + tradeDate, HttpStatus.NOT_FOUND));
        return KlineVO.fromEntity(entity);
    }

    @Transactional(readOnly = true)
    public KlineStatsVO getStats(String symbol) {
        long count = klineRepository.countBySymbol(symbol);
        var latest = klineRepository.findFirstBySymbolOrderByDateDesc(symbol);
        var first = klineRepository.findBySymbolAndDateBetweenOrderByDateAsc(
            symbol,
            LocalDate.of(1900, 1, 1),
            LocalDate.of(9999, 12, 31)
        );
        LocalDate firstDate = first.isEmpty() ? null : first.get(0).getDate();

        return KlineStatsVO.builder()
            .symbol(symbol)
            .totalCount(count)
            .firstDate(firstDate)
            .lastDate(latest.map(e -> e.getDate()).orElse(null))
            .latestClose(latest.map(e -> e.getClose()).orElse(null))
            .build();
    }

    @Transactional
    public KlineCollectVO collect(KlineCollectRequest request) {
        Collector collector = collectorRegistry.getKlineCollector();
        try {
            KlineCollectVO result = collector.collect(request.getSymbol(), request.getDays());
            return KlineCollectVO.builder()
                .symbol(request.getSymbol())
                .fetched(result.getFetched())
                .saved(result.getSaved())
                .startDate(result.getStartDate())
                .endDate(result.getEndDate())
                .message("采集完成")
                .build();
        } catch (Exception e) {
            log.error("K线采集失_ {}", request.getSymbol(), e);
            throw new BusinessException("collect", "COLLECTION_ERROR",
                "数据采集失败 [tushare]: " + e.getMessage(), HttpStatus.BAD_GATEWAY);
        }
    }

    @Transactional
    public Map<String, KlineCollectVO> collectBatch(List<String> symbols, int days) {
        Map<String, KlineCollectVO> results = new HashMap<>();
        for (String symbol : symbols) {
            try {
                KlineCollectRequest req = KlineCollectRequest.builder()
                    .symbol(symbol)
                    .days(days)
                    .build();
                results.put(symbol, collect(req));
            } catch (Exception e) {
                log.warn("批量采集失败: {}", symbol, e);
                results.put(symbol, KlineCollectVO.builder()
                    .symbol(symbol)
                    .fetched(0)
                    .saved(0)
                    .message("FAILED: " + e.getMessage())
                    .build());
            }
        }
        return results;
    }

    @Transactional
    public void deleteAll(String symbol) {
        klineRepository.deleteBySymbol(symbol);
    }

    @Transactional
    public void deleteByDate(String symbol, LocalDate tradeDate) {
        klineRepository.deleteBySymbolAndDate(symbol, tradeDate);
    }
}
