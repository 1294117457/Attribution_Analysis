package com.attribution.market.service.impl;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import org.springframework.stereotype.Service;

import com.attribution.common.exception.BusinessException;
import com.attribution.common.mybatis.TopN;
import com.attribution.common.response.PageResult;
import com.attribution.market.converter.MarketConverter;
import com.attribution.market.dto.StockPanelQuery;
import com.attribution.market.dto.StockUpdateRequest;
import com.attribution.market.entity.StockInfoPO;
import com.attribution.market.mapper.StockInfoMapper;
import com.attribution.market.service.StockInfoService;
import com.attribution.market.vo.ConceptBriefVO;
import com.attribution.market.vo.ConceptMainVO;
import com.attribution.market.vo.PoolMembershipVO;
import com.attribution.market.vo.StockBriefVO;
import com.attribution.market.vo.StockInfoVO;
import com.attribution.market.vo.StockMetaVO;
import com.attribution.market.vo.StockPanelVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class StockInfoServiceImpl implements StockInfoService {
    private final StockInfoMapper stockInfoMapper;

    /** 概念类型优先级：行业 > 主题 > 事件 > 风格 > 地域 > 其他 */
    static final Map<String, Integer> CONCEPT_TYPE_PRIORITY =
            Map.of("industry", 1, "theme", 2, "event", 3, "style", 4, "region", 5, "other", 6);

    /** 主概念展示位数 */
    private static final int MAIN_CONCEPT_LIMIT = 3;

    /** 元信息扫描的最大股票数（避免全表扫描） */
    private static final int META_SCAN_LIMIT = 10000;

    @Override
    public StockMetaVO meta() {
        Set<String> industries = new TreeSet<>();
        Set<String> markets = new TreeSet<>();
        Set<String> exchanges = new TreeSet<>();
        var wrapper =
                new LambdaQueryWrapper<StockInfoPO>()
                        .select(
                                StockInfoPO::getIndustry,
                                StockInfoPO::getMarket,
                                StockInfoPO::getExchange);
        for (StockInfoPO stock : TopN.query(stockInfoMapper, wrapper, META_SCAN_LIMIT)) {
            if (stock.getIndustry() != null && !stock.getIndustry().isBlank())
                industries.add(stock.getIndustry());
            if (stock.getMarket() != null && !stock.getMarket().isBlank()) markets.add(stock.getMarket());
            if (stock.getExchange() != null && !stock.getExchange().isBlank())
                exchanges.add(stock.getExchange());
        }
        return MarketConverter.toStockMetaVO(
                new ArrayList<>(industries), new ArrayList<>(markets), new ArrayList<>(exchanges));
    }

    @Override
    public StockInfoVO get(String symbol) {
        StockInfoPO stock =
                stockInfoMapper.selectOne(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (stock == null) throw new BusinessException(404, "股票不存在");
        return MarketConverter.toStockInfoVO(stock);
    }

    @Override
    public StockInfoVO upsert(String symbol, String name, String industry, String market) {
        StockInfoPO existing =
                stockInfoMapper.selectOne(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (existing == null) {
            existing = new StockInfoPO();
            existing.setSymbol(symbol);
        }
        existing.setName(name);
        existing.setIndustry(industry);
        existing.setMarket(market);
        if (existing.getId() == null) stockInfoMapper.insert(existing);
        else stockInfoMapper.updateById(existing);
        return MarketConverter.toStockInfoVO(existing);
    }

    @Override
    public StockInfoVO patch(String symbol, StockUpdateRequest request) {
        StockInfoPO existing =
                stockInfoMapper.selectOne(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (existing == null) throw new BusinessException(404, "股票不存在");
        if (request.getName() != null) existing.setName(request.getName());
        if (request.getIndustry() != null) existing.setIndustry(request.getIndustry());
        if (request.getMarket() != null) existing.setMarket(request.getMarket());
        stockInfoMapper.updateById(existing);
        return MarketConverter.toStockInfoVO(existing);
    }

    @Override
    public void delete(String symbol) {
        long deleted =
                stockInfoMapper.delete(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (deleted == 0) throw new BusinessException(404, "股票不存在");
    }

    // ── 关联数据装配 ─────────────────────────────────────────

    /** 批量取股票所属自选池，按 symbol 分组 */
    private Map<String, List<PoolMembershipVO>> poolMapBySymbol(List<String> symbols) {
        Map<String, List<PoolMembershipVO>> poolsBySymbol = new HashMap<>();
        for (String symbol : symbols) poolsBySymbol.put(symbol, new ArrayList<>());
        if (symbols.isEmpty()) return poolsBySymbol;
        for (StockInfoMapper.PoolMembershipRow row : stockInfoMapper.selectPoolMemberships(symbols)) {
            PoolMembershipVO vo = new PoolMembershipVO();
            vo.setPoolId(row.getPoolId());
            vo.setName(row.getName());
            vo.setPoolType(row.getPoolType());
            vo.setJoinedAt(null);
            poolsBySymbol.computeIfAbsent(row.getSymbol(), key -> new ArrayList<>()).add(vo);
        }
        return poolsBySymbol;
    }

    /** 批量取股票所属概念，按 symbol 分组 */
    private Map<String, List<ConceptBriefVO>> conceptBriefMapBySymbol(List<String> symbols) {
        Map<String, List<ConceptBriefVO>> conceptsBySymbol = new HashMap<>();
        for (String symbol : symbols) conceptsBySymbol.put(symbol, new ArrayList<>());
        if (symbols.isEmpty()) return conceptsBySymbol;
        for (StockInfoMapper.ConceptBriefRow row : stockInfoMapper.selectConceptBriefs(symbols)) {
            ConceptBriefVO vo = new ConceptBriefVO();
            vo.setConceptId(row.getConceptId());
            vo.setName(row.getName());
            vo.setSource(row.getSource());
            vo.setConceptType(row.getConceptType());
            conceptsBySymbol.computeIfAbsent(row.getSymbol(), key -> new ArrayList<>()).add(vo);
        }
        return conceptsBySymbol;
    }

    /** 取主概念（按类型优先级 + 名称排序），并标记展示位次 */
    private List<ConceptMainVO> toMainConcepts(List<ConceptBriefVO> briefs, int maxConcepts) {
        List<ConceptBriefVO> sorted = new ArrayList<>(briefs);
        sorted.sort(
                (a, b) -> {
                    int priorityA =
                            CONCEPT_TYPE_PRIORITY.getOrDefault(
                                    a.getConceptType() == null ? "other" : a.getConceptType(), 99);
                    int priorityB =
                            CONCEPT_TYPE_PRIORITY.getOrDefault(
                                    b.getConceptType() == null ? "other" : b.getConceptType(), 99);
                    if (priorityA != priorityB) return Integer.compare(priorityA, priorityB);
                    return String.valueOf(a.getName()).compareTo(String.valueOf(b.getName()));
                });
        List<ConceptMainVO> mainConcepts = new ArrayList<>();
        for (int i = 0; i < Math.min(maxConcepts, sorted.size()); i++) {
            ConceptBriefVO brief = sorted.get(i);
            ConceptMainVO conceptVO = new ConceptMainVO();
            conceptVO.setConceptId(brief.getConceptId());
            conceptVO.setName(brief.getName());
            conceptVO.setSource(brief.getSource());
            conceptVO.setConceptType(brief.getConceptType());
            conceptVO.setDisplayOrder(i + 1);
            conceptVO.setSnapshot(null);
            mainConcepts.add(conceptVO);
        }
        return mainConcepts;
    }

    // ── 面板列表 ─────────────────────────────────────────────

    @Override
    public PageResult<StockPanelVO> page(StockPanelQuery query) {
        var wrapper = new LambdaQueryWrapper<StockInfoPO>();
        if (query.getKeyword() != null && !query.getKeyword().isBlank())
            wrapper.and(
                    condition ->
                            condition
                                    .like(StockInfoPO::getSymbol, query.getKeyword())
                                    .or()
                                    .like(StockInfoPO::getName, query.getKeyword())
                                    .or()
                                    .like(StockInfoPO::getTsCode, query.getKeyword()));
        if (query.getIndustry() != null && !query.getIndustry().isBlank())
            wrapper.eq(StockInfoPO::getIndustry, query.getIndustry());
        if (query.getMarket() != null && !query.getMarket().isBlank())
            wrapper.eq(StockInfoPO::getMarket, query.getMarket());
        if (query.getExchange() != null && !query.getExchange().isBlank())
            wrapper.eq(StockInfoPO::getExchange, query.getExchange());
        if (query.getIsHs() != null && !query.getIsHs().isBlank())
            wrapper.eq(StockInfoPO::getIsHs, query.getIsHs());
        if (query.getListStatus() != null
                && !query.getListStatus().isBlank()
                && !query.getListStatus().equals("全部"))
            wrapper.eq(StockInfoPO::getListStatus, query.getListStatus());
        // excludeSt=true 表示只保留非 ST（排除 ST），false 表示只看 ST
        if (query.getExcludeSt() != null) {
            if (query.getExcludeSt()) wrapper.notLike(StockInfoPO::getName, "ST");
            else wrapper.like(StockInfoPO::getName, "ST");
        }
        if (query.getConceptId() != null) {
            List<String> symbols = stockInfoMapper.selectSymbolsByConceptId(query.getConceptId());
            if (symbols.isEmpty()) return PageResult.of(0, List.of(), query.getPage(), query.getPageSize());
            wrapper.in(StockInfoPO::getSymbol, symbols);
        }
        if (query.getMinTotalMv() != null) {
            List<String> symbols = stockInfoMapper.selectSymbolsByMinTotalMv(query.getMinTotalMv());
            if (symbols.isEmpty()) return PageResult.of(0, List.of(), query.getPage(), query.getPageSize());
            wrapper.in(StockInfoPO::getSymbol, symbols);
        }
        // count 查询不能带 orderBy（PostgreSQL: column must appear in GROUP BY），
        // 所以先统计总数，再加排序
        long total = stockInfoMapper.selectCount(wrapper);
        wrapper.orderByAsc(StockInfoPO::getSymbol);
        var pageParam = new Page<StockInfoPO>(query.getPage(), query.getPageSize());
        List<StockInfoPO> records = stockInfoMapper.selectPage(pageParam, wrapper).getRecords();

        List<String> symbols = records.stream().map(StockInfoPO::getSymbol).toList();
        Map<String, List<PoolMembershipVO>> pools =
                query.isWithPools() ? poolMapBySymbol(symbols) : Map.of();
        Map<String, List<ConceptBriefVO>> concepts =
                query.isWithConcepts() ? conceptBriefMapBySymbol(symbols) : Map.of();
        // 统计指标一次批量查询，避免逐行查库（N+1）
        Map<String, StockInfoMapper.StockStatRow> stats = statMapBySymbol(symbols);

        List<StockPanelVO> list = new ArrayList<>();
        for (StockInfoPO stock : records) {
            StockPanelVO stockVO = new StockPanelVO();
            stockVO.setSymbol(stock.getSymbol());
            stockVO.setTsCode(stock.getTsCode());
            stockVO.setName(stock.getName());
            stockVO.setArea(stock.getArea());
            stockVO.setIndustry(stock.getIndustry());
            stockVO.setMarket(stock.getMarket());
            stockVO.setExchange(stock.getExchange());
            stockVO.setListDate(MarketConverter.formatListDate(stock.getListDate()));
            stockVO.setListStatus(stock.getListStatus());
            stockVO.setIsHs(stock.getIsHs());
            stockVO.setActName(stock.getActName());
            stockVO.setActEntType(stock.getActEntType());
            stockVO.setTotalShares(stock.getTotalShares());

            String symbol = stock.getSymbol();
            StockInfoMapper.StockStatRow stat = stats.get(symbol);
            if (stat != null) {
                stockVO.setRecordCount(stat.getRecordCount() == null ? 0 : stat.getRecordCount().intValue());
                stockVO.setKlineStart(stat.getKlineStart());
                stockVO.setKlineEnd(stat.getKlineEnd());
                stockVO.setLatestClose(stat.getLatestClose());
                stockVO.setTotalMv(stat.getTotalMv());
                stockVO.setPeTtm(stat.getPeTtm());
                stockVO.setProfitMargin(toDouble(stat.getProfitMargin()));
            }

            stockVO.setPools(
                    query.isWithPools()
                            ? pools.getOrDefault(symbol, List.of())
                            : List.of());
            if (query.isWithConcepts()) {
                List<ConceptBriefVO> briefs = concepts.getOrDefault(symbol, List.of());
                stockVO.setConcepts(toMainConcepts(briefs, MAIN_CONCEPT_LIMIT));
                stockVO.setConceptsOverflow(Math.max(0, briefs.size() - MAIN_CONCEPT_LIMIT));
            } else {
                stockVO.setConcepts(List.of());
                stockVO.setConceptsOverflow(0);
            }
            list.add(stockVO);
        }
        return PageResult.of(total, list, query.getPage(), query.getPageSize());
    }

    /** 批量取面板统计指标，按 symbol 索引 */
    private Map<String, StockInfoMapper.StockStatRow> statMapBySymbol(List<String> symbols) {
        Map<String, StockInfoMapper.StockStatRow> stats = new HashMap<>();
        if (symbols.isEmpty()) return stats;
        for (StockInfoMapper.StockStatRow row : stockInfoMapper.selectStockStats(symbols))
            stats.put(row.getSymbol(), row);
        return stats;
    }

    @Override
    public Map<String, StockBriefVO> briefs(List<String> symbols) {
        Map<String, StockBriefVO> briefBySymbol = new HashMap<>();
        if (symbols == null || symbols.isEmpty()) return briefBySymbol;
        var wrapper =
                new LambdaQueryWrapper<StockInfoPO>()
                        .select(
                                StockInfoPO::getSymbol,
                                StockInfoPO::getName,
                                StockInfoPO::getIndustry,
                                StockInfoPO::getMarket,
                                StockInfoPO::getExchange)
                        .in(StockInfoPO::getSymbol, symbols.stream().distinct().toList());
        for (StockInfoPO row : stockInfoMapper.selectList(wrapper)) {
            StockBriefVO brief = new StockBriefVO();
            brief.setSymbol(row.getSymbol());
            brief.setName(row.getName());
            brief.setIndustry(row.getIndustry());
            brief.setMarket(row.getMarket());
            brief.setExchange(row.getExchange());
            briefBySymbol.put(row.getSymbol(), brief);
        }
        return briefBySymbol;
    }

    /** BigDecimal → Double（null 安全） */
    private Double toDouble(BigDecimal value) {
        return value == null ? null : value.doubleValue();
    }
}
