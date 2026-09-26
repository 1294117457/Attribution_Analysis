package com.attribution.infrastructure.query;

import com.attribution.domain.entity.ConceptEntity;
import com.attribution.domain.entity.ConceptMemberEntity;
import com.attribution.domain.entity.FinDailyBasicEntity;
import com.attribution.domain.entity.FinReportEntity;
import com.attribution.domain.entity.StockInfoEntity;
import com.attribution.domain.entity.TechKlineDailyEntity;
import com.attribution.domain.repository.CapMoneyflowRepository;
import com.attribution.domain.repository.ConceptMemberRepository;
import com.attribution.domain.repository.ConceptRepository;
import com.attribution.domain.repository.FinDailyBasicRepository;
import com.attribution.domain.repository.FinReportRepository;
import com.attribution.domain.repository.StockInfoRepository;
import com.attribution.domain.repository.StockPanelComposeRepository;
import com.attribution.domain.repository.StockPoolMemberRepository;
import com.attribution.domain.repository.TechKlineDailyRepository;
import com.attribution.domain.service.ProfitabilityDomainService;
import com.attribution.interfaces.dto.ConceptBriefVO;
import com.attribution.interfaces.dto.PoolBriefVO;
import com.attribution.interfaces.dto.StockPanelQuery;
import com.attribution.interfaces.dto.StockPanelRowVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Repository;
import org.springframework.util.StringUtils;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 面板组合查询实现 - 内存聚合，避免超复杂 SQL_ */
@Slf4j
@Repository
@RequiredArgsConstructor
public class StockPanelComposeRepositoryImpl implements StockPanelComposeRepository {

    private final StockInfoRepository stockInfoRepository;
    private final TechKlineDailyRepository klineRepository;
    private final FinDailyBasicRepository dailyBasicRepository;
    private final FinReportRepository finReportRepository;
    private final CapMoneyflowRepository moneyflowRepository;
    private final ConceptRepository conceptRepository;
    private final ConceptMemberRepository conceptMemberRepository;
    private final StockPoolMemberRepository poolMemberRepository;
    private final ProfitabilityDomainService profitabilityDomainService;

    @Override
    public List<StockPanelRowVO> queryPanel(StockPanelQuery query) {
        LocalDate tradeDate = resolveTradeDate(query.getTradeDate());
        query.setTradeDate(tradeDate);

        org.springframework.data.domain.Pageable pageable = buildPageable(
            query.getPage(), query.getSize(), query.getSortBy(), query.getSortDir());
        List<StockInfoEntity> stocks = stockInfoRepository.findPanelPage(
            query.getKeyword(),
            query.getIndustry(),
            pageable
        );

        if (stocks.isEmpty()) {
            return Collections.emptyList();
        }

        List<String> symbols = stocks.stream().map(StockInfoEntity::getSymbol).toList();

        Map<String, TechKlineDailyEntity> klineMap = klineRepository
            .findByDateAndSymbolIn(tradeDate, symbols).stream()
            .collect(Collectors.toMap(TechKlineDailyEntity::getSymbol, Function.identity()));

        Map<String, FinDailyBasicEntity> basicMap = dailyBasicRepository
            .findByTradeDateAndSymbolIn(tradeDate, symbols).stream()
            .collect(Collectors.toMap(FinDailyBasicEntity::getSymbol, Function.identity()));

        Map<String, Double> mfMap = moneyflowRepository
            .findByTradeDateAndSymbolIn(tradeDate, symbols).stream()
            .collect(Collectors.toMap(
                m -> m.getSymbol(),
                m -> m.getNetMfAmount() == null ? 0d : m.getNetMfAmount(),
                (a, b) -> a));

        Map<String, List<ConceptBriefVO>> conceptMap =
            Boolean.TRUE.equals(query.getWithConcepts())
                ? loadConceptMap(symbols)
                : Collections.emptyMap();

        // with_pools=true: 一次性查所有 symbol 的池与 K 线统计，避免 N+1
        Map<String, List<PoolBriefVO>> poolMap =
            Boolean.TRUE.equals(query.getWithPools())
                ? loadPoolMap(symbols)
                : Collections.emptyMap();
        Map<String, long[]> klineStatMap =
            Boolean.TRUE.equals(query.getWithPools())
                ? loadKlineStats(symbols)
                : Collections.emptyMap();

        // 一次性加载 page 内全部 symbol 的财报，按 symbol 取 end_date 最大行
        // 避免 N+1（一页 20~200 行也只需一次 SQL）
        Map<String, FinReportEntity> latestFinReportMap = loadLatestFinReports(symbols);

        return stocks.stream()
            .map(s -> merge(s, klineMap, basicMap, mfMap, conceptMap, poolMap, klineStatMap, latestFinReportMap))
            .toList();
    }

    /**
     * 批量加载 page 内所有 symbol 的最新一期财报（end_date 最大的那一行）。
     * <p>
     * 取一次所有行的方法 {@link FinReportRepository#findAllBySymbols}，
     * 在内存里按 symbol 分组选最大 end_date。
     */
    private Map<String, FinReportEntity> loadLatestFinReports(List<String> symbols) {
        List<FinReportEntity> all = finReportRepository.findAllBySymbols(symbols);
        if (all == null || all.isEmpty()) {
            return Collections.emptyMap();
        }
        Map<String, FinReportEntity> latest = new HashMap<>(all.size());
        for (FinReportEntity r : all) {
            if (r.getEndDate() == null) continue;
            FinReportEntity existing = latest.get(r.getSymbol());
            if (existing == null
                || existing.getEndDate() == null
                || r.getEndDate().isAfter(existing.getEndDate())) {
                latest.put(r.getSymbol(), r);
            }
        }
        return latest;
    }

    @Override
    public long countPanel(StockPanelQuery query) {
        return stockInfoRepository.countPanel(query.getKeyword(), query.getIndustry());
    }

    private StockPanelRowVO merge(StockInfoEntity stock,
                                  Map<String, TechKlineDailyEntity> klineMap,
                                  Map<String, FinDailyBasicEntity> basicMap,
                                  Map<String, Double> mfMap,
                                  Map<String, List<ConceptBriefVO>> conceptMap,
                                  Map<String, List<PoolBriefVO>> poolMap,
                                  Map<String, long[]> klineStatMap,
                                  Map<String, FinReportEntity> latestFinReportMap) {
        TechKlineDailyEntity k = klineMap.get(stock.getSymbol());
        FinDailyBasicEntity b = basicMap.get(stock.getSymbol());

        StockPanelRowVO.StockPanelRowVOBuilder builder = StockPanelRowVO.builder()
            // 基本信息（来自 stock_infos）
            .symbol(stock.getSymbol())
            .tsCode(stock.getTsCode())
            .name(stock.getName())
            .area(stock.getArea())
            .industry(stock.getIndustry())
            .market(stock.getMarket())
            .exchange(stock.getExchange())
            .listDate(stock.getListDate())
            .delistDate(stock.getDelistDate())
            .listStatus(stock.getListStatus())
            .isHs(stock.getIsHs())
            .actName(stock.getActName())
            .actEntType(stock.getActEntType())
            // 当日行情
            .latestClose(null)  // 在 K 线分支里填充（=close）
            .preClose(null)     // tech_kline_dailys 表无 pre_close 列
            .change(null)       // tech_kline_dailys 表无 change 列
            .turnoverRate(null) // tech_kline_dailys 表无 turnover_rate 列
            // profit_margin 不在这里硬编码 null，由收尾阶段交给 ProfitabilityDomainService 计算
            // 关联
            .concepts(conceptMap.getOrDefault(stock.getSymbol(), Collections.emptyList()))
            .pools(poolMap.getOrDefault(stock.getSymbol(), Collections.emptyList()));

        if (k != null) {
            builder.tradeDate(k.getDate())
                .close(k.getClose())
                .latestClose(k.getClose())  // 暴露给前端的别名
                .open(k.getOpen())
                .high(k.getHigh())
                .low(k.getLow())
                .pctChange(k.getChangePct())
                .volume(k.getVolume())
                .amount(k.getAmount())
                .ma5(k.getMa5()).ma10(k.getMa10()).ma20(k.getMa20()).ma60(k.getMa60())
                .ema12(k.getEma12()).ema26(k.getEma26())
                .macd(k.getMacdBar())
                .macdDiff(k.getMacdDif())
                .macdDea(k.getMacdDea())
                .rsi6(k.getRsi6()).rsi12(k.getRsi12()).rsi24(k.getRsi24())
                .kdjK(k.getKdjK()).kdjD(k.getKdjD()).kdjJ(k.getKdjJ())
                .bollMid(k.getBollMid())
                .bollUpper(k.getBollUp())
                .bollLower(k.getBollDn());
        }

        if (b != null) {
            builder.pe(b.getPe()).peTtm(b.getPeTtm()).pb(b.getPb())
                .ps(b.getPs()).psTtm(b.getPsTtm())
                .dvRatio(b.getDvRatio()).dvTtm(b.getDvTtm())
                .totalMv(b.getTotalMv()).circMv(b.getCircMv())
                .totalShare(b.getTotalShare()).floatShare(b.getFloatShare());
        }

        // K 线统计（with_pools=true 时附带）
        long[] stat = klineStatMap.get(stock.getSymbol());
        if (stat != null) {
            builder.recordCount(stat[0]);
            builder.klineStart(stat[1] > 0 ? LocalDate.ofEpochDay(stat[1]).toString() : null);
            builder.klineEnd(stat[2] > 0 ? LocalDate.ofEpochDay(stat[2]).toString() : null);
        }

        builder.netMfAmount(mfMap.getOrDefault(stock.getSymbol(), 0d));

        // ── 派生指标：净利润率% ─────────────────────────────
        // fin_reports 物理表无 profit_margin 列，由 FinReportEntity (n_income_attr_p / revenue)
        // 派生出 n_income_attr_p / revenue × 100。本阶段只做"装配 + 调用"，具体规则交给
        // ProfitabilityDomainService（纯计算、不可访问 IO）。
        FinReportEntity latestReport = latestFinReportMap.get(stock.getSymbol());
        Double profitMargin = profitabilityDomainService.computeProfitMarginPct(latestReport);
        if (profitMargin != null) {
            builder.profitMargin(profitMargin);
        }

        return builder.build();
    }

    private LocalDate resolveTradeDate(LocalDate given) {
        if (given != null) {
            return given;
        }
        // 估值表（fin_daily_basics）的最新交易日最有指示意义：
        // 它覆盖了所有"有估值数据的"股票，能确保 pe_ttm/total_mv 等字段不丢。
        // 如果某个股票当天没估值数据，下面的 join 仍然走不到，
        // 但我们至少能在最新有数据的那一天做联合展示。
        return dailyBasicRepository.findLastTradeDate()
            .or(() -> klineRepository.findLastTradeDate())
            .orElse(LocalDate.now());
    }

    private org.springframework.data.domain.Pageable buildPageable(
            int page, int size, String sortBy, String sortDir) {
        int p = Math.max(0, page - 1);
        int s = Math.max(1, size);
        if (!StringUtils.hasText(sortBy)) {
            return org.springframework.data.domain.PageRequest.of(p, s);
        }
        org.springframework.data.domain.Sort.Direction dir =
            "asc".equalsIgnoreCase(sortDir)
                ? org.springframework.data.domain.Sort.Direction.ASC
                : org.springframework.data.domain.Sort.Direction.DESC;
        String field = mapSortField(sortBy);
        return org.springframework.data.domain.PageRequest.of(p, s,
            org.springframework.data.domain.Sort.by(dir, field));
    }

    private String mapSortField(String sortBy) {
        if (sortBy == null) return "symbol";
        return switch (sortBy.toLowerCase()) {
            case "symbol", "name", "industry", "market", "list_date", "listdate" -> sortBy;
            default -> "symbol";
        };
    }

    private Map<String, List<ConceptBriefVO>> loadConceptMap(List<String> symbols) {
        List<ConceptMemberEntity> members = conceptMemberRepository.findActiveBySymbolIn(
            symbols, LocalDate.now());
        if (members.isEmpty()) {
            return Collections.emptyMap();
        }
        List<Long> ids = members.stream().map(ConceptMemberEntity::getConceptId).distinct().toList();
        Map<Long, ConceptEntity> conceptMap = conceptRepository.findAllById(ids).stream()
            .collect(Collectors.toMap(ConceptEntity::getId, Function.identity()));
        return members.stream().collect(Collectors.groupingBy(
            ConceptMemberEntity::getSymbol,
            Collectors.mapping(m -> {
                ConceptEntity c = conceptMap.get(m.getConceptId());
                String id = String.valueOf(m.getConceptId());
                String name = c != null ? c.getName() : m.getName();
                String source = c != null ? c.getSource() : null;
                return ConceptBriefVO.builder()
                    .code(id)
                    .conceptId(id)
                    .name(name)
                    .source(source)
                    .build();
            }, Collectors.toList())
        ));
    }

    private Map<String, List<PoolBriefVO>> loadPoolMap(List<String> symbols) {
        List<Object[]> rows = poolMemberRepository.findPoolsBySymbols(symbols);
        Map<String, List<PoolBriefVO>> result = new HashMap<>();
        for (Object[] r : rows) {
            // SELECT m.symbol, m.poolId, p.name, p.poolType, m.addedAt
            String symbol = (String) r[0];
            Long poolId = ((Number) r[1]).longValue();
            String poolName = (String) r[2];
            String poolType = (String) r[3];
            java.time.LocalDateTime joinedAt = r[4] != null
                ? ((java.sql.Timestamp) r[4]).toLocalDateTime() : null;
            result.computeIfAbsent(symbol, k -> new ArrayList<>()).add(
                PoolBriefVO.builder()
                    .poolId(poolId)
                    .name(poolName)
                    .poolType(poolType)
                    .joinedAt(joinedAt)
                    .build()
            );
        }
        return result;
    }

    private Map<String, long[]> loadKlineStats(List<String> symbols) {
        List<Object[]> rows = klineRepository.aggregateStatsBySymbols(symbols);
        Map<String, long[]> result = new HashMap<>();
        for (Object[] r : rows) {
            String symbol = (String) r[0];
            LocalDate min = (LocalDate) r[1];
            LocalDate max = (LocalDate) r[2];
            long count = ((Number) r[3]).longValue();
            result.put(symbol, new long[]{
                count,
                min == null ? -1 : min.toEpochDay(),
                max == null ? -1 : max.toEpochDay()
            });
        }
        return result;
    }
}
