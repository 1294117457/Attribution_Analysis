package com.attribution.infrastructure.adapter.collector.tushare;

import com.attribution.application.service.CollectorRegistry;
import com.attribution.domain.entity.StockInfoEntity;
import com.attribution.domain.entity.TechKlineDailyEntity;
import com.attribution.domain.repository.StockInfoRepository;
import com.attribution.domain.repository.TechKlineDailyRepository;
import com.attribution.domain.service.IndicatorCalculator;
import com.attribution.infrastructure.adapter.collector.Collector;
import com.attribution.interfaces.dto.kline.KlineCollectVO;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

/**
 * Tushare K 线采集器
 *
 * <p>替代 Python TushareFetcher，从 Tushare Pro API 拉取日 K 线数据并写入 PostgreSQL。
 * 采集后调用 {@link IndicatorCalculator} 计算 17 个技术指标（MA/EMA/MACD/RSI/KDJ/BOLL），
 * 指标与 K 线一同入库（方案 A）。
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class TushareKlineCollector implements Collector {

    private final TushareApiClient apiClient;
    private final TechKlineDailyRepository klineRepository;
    private final StockInfoRepository stockInfoRepository;
    private final CollectorRegistry collectorRegistry;
    private final IndicatorCalculator indicatorCalculator;

    @PostConstruct
    public void register() {
        collectorRegistry.register("kline", this);
    }

    @Override
    public String name() {
        return "Tushare";
    }

    @Override
    public KlineCollectVO collect(String symbol, int days) {
        LocalDate end = LocalDate.now();
        // MA60 需要至少 60 条历史数据；多取 80 条确保窗口足够
        int lookback = Math.max(days, 80);
        LocalDate start = end.minusDays(lookback);

        log.info("开始采集 {} 日 K 线数据，区间 {} -> {}", symbol, start, end);

        // ── 拉取原始数据 ──────────────────────────────────────
        List<Object[]> items = fetchRawData(symbol, start, end);
        if (items.isEmpty()) {
            log.warn("{} 未获取到任何 K 线数据（代码无效或无交易记录）", symbol);
            return KlineCollectVO.builder()
                    .symbol(symbol)
                    .fetched(0)
                    .saved(0)
                    .message("未获取到数据（代码无效或无交易记录）")
                    .build();
        }

        String stockName = stockInfoRepository.findBySymbol(symbol)
                .map(StockInfoEntity::getName)
                .orElse(null);

        // ── 构造 entity（无指标）并保存 ───────────────────────
        List<TechKlineDailyEntity> newEntities = new ArrayList<>();
        for (Object[] row : items) {
            TechKlineDailyEntity entity = parseRow(symbol, stockName, row);
            if (entity != null) {
                newEntities.add(entity);
            }
        }

        if (!newEntities.isEmpty()) {
            klineRepository.saveAll(newEntities);
            log.info("{} 写入 {} 条原始 K 线", symbol, newEntities.size());
        }

        // ── 计算 17 个技术指标（方案 A：采集时一并入库） ──────
        recalculateIndicators(symbol);

        return KlineCollectVO.builder()
                .symbol(symbol)
                .fetched(items.size())
                .saved(newEntities.size())
                .startDate(start)
                .endDate(end)
                .message("采集完成（含指标计算）")
                .build();
    }

    /**
     * 重新计算指定股票的指标。
     * <p>
     * 取最近 100 条 K 线（按日期升序），调用 {@link IndicatorCalculator} 填充 17 个指标列，
     * 再整体 UPSERT 回数据库。
     *
     * @param symbol 股票代码
     */
    public void recalculateIndicators(String symbol) {
        // 取足够多的历史数据（MA60 需要至少 60 条，多取一些保险）
        List<TechKlineDailyEntity> history =
                klineRepository.findBySymbolOrderByDateAsc(symbol);

        if (history.size() < 2) {
            log.debug("{} 历史数据不足 2 条，跳过指标计算", symbol);
            return;
        }

        // 限制只取最近 100 条，避免每次全量重算开销过大
        int fromIndex = Math.max(0, history.size() - 100);
        List<TechKlineDailyEntity> window = history.subList(fromIndex, history.size());

        // 按日期升序（指标计算依赖此前提）
        window.sort(Comparator.comparing(TechKlineDailyEntity::getDate));

        // 计算指标（原地修改 entity）
        indicatorCalculator.enrich(window);

        // 保存含指标的 entity
        klineRepository.saveAll(window);
        log.info("{} 指标计算完成，窗口 {} 条", symbol, window.size());
    }

    // ── 私有辅助方法 ───────────────────────────────────────

    private List<Object[]> fetchRawData(String symbol, LocalDate start, LocalDate end) {
        java.util.Map<String, Object> params = new java.util.HashMap<>();
        params.put("ts_code", symbol);
        params.put("start_date", TushareApiClient.formatDate(start));
        params.put("end_date", TushareApiClient.formatDate(end));

        TushareResponse response = apiClient.call("daily", params,
                "ts_code,trade_date,open,high,low,close,vol,amount");

        if (response.getCode() != 0) {
            throw new RuntimeException("Tushare API 错误: " + response.getMsg());
        }

        return apiClient.parseItems(response);
    }

    private TechKlineDailyEntity parseRow(String symbol, String name, Object[] row) {
        String tsCode = row[0] != null ? row[0].toString() : symbol;
        LocalDate tradeDate = LocalDate.parse(row[1].toString(),
                java.time.format.DateTimeFormatter.BASIC_ISO_DATE);
        Double open = parseDouble(row[2]);
        Double high = parseDouble(row[3]);
        Double low = parseDouble(row[4]);
        Double close = parseDouble(row[5]);
        Long volume = parseLong(row[6]);
        Double amount = parseDouble(row[7]);

        if (open == null || close == null) {
            return null;
        }

        // change_pct 依赖前一条收盘价，从已有记录中查
        Double changePct = null;
        Optional<TechKlineDailyEntity> prev =
                klineRepository.findFirstBySymbolOrderByDateDesc(symbol);
        if (prev.isPresent() && prev.get().getClose() != null && prev.get().getClose() != 0) {
            changePct = (close - prev.get().getClose()) / prev.get().getClose() * 100.0;
        }

        return TechKlineDailyEntity.builder()
                .symbol(symbol)
                .name(name)
                .date(tradeDate)
                .open(open)
                .high(high)
                .low(low)
                .close(close)
                .volume(volume != null ? volume : 0L)
                .amount(amount != null ? amount : 0.0)
                .changePct(changePct)
                // 17 个技术指标字段初始为 null，由 IndicatorCalculator.enrich() 填充
                .build();
    }

    private Double parseDouble(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(v.toString());
        } catch (Exception e) {
            return null;
        }
    }

    private Long parseLong(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(v.toString());
        } catch (Exception e) {
            return null;
        }
    }
}
