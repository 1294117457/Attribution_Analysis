package com.attribution.concept.service.impl;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.stereotype.Service;

import com.attribution.collector.client.CollectorService;
import com.attribution.common.exception.BusinessException;
import com.attribution.common.mybatis.TopN;
import com.attribution.common.response.PageResult;
import com.attribution.concept.converter.ConceptConverter;
import com.attribution.concept.dto.ConceptBoardQuery;
import com.attribution.concept.dto.ConceptKlineQuery;
import com.attribution.concept.dto.ConceptMemberQuery;
import com.attribution.concept.dto.ConceptQuery;
import com.attribution.concept.entity.ConceptIndexPO;
import com.attribution.concept.entity.ConceptPO;
import com.attribution.concept.mapper.ConceptIndexMapper;
import com.attribution.concept.mapper.ConceptMapper;
import com.attribution.concept.mapper.ConceptMemberMapper;
import com.attribution.concept.service.ConceptService;
import com.attribution.concept.vo.*;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class ConceptServiceImpl implements ConceptService {
    private final ConceptMapper conceptMapper;
    private final ConceptMemberMapper conceptMemberMapper;
    private final ConceptIndexMapper conceptIndexMapper;
    private final CollectorService collectorService;

    static final List<String> CONCEPT_TYPE_ORDER =
            List.of("industry", "theme", "style", "region", "event", "other");

    // ── 概念列表 ─────────────────────────────────────────────

    @Override
    public PageResult<ConceptVO> list(ConceptQuery query) {
        var wrapper = new LambdaQueryWrapper<ConceptPO>();
        if (query.getKeyword() != null && !query.getKeyword().isBlank())
            wrapper.and(
                    condition ->
                            condition
                                    .like(ConceptPO::getName, query.getKeyword())
                                    .or()
                                    .eq(ConceptPO::getIndexCode, query.getKeyword()));
        if (query.getIsActive() != null) wrapper.eq(ConceptPO::getIsActive, query.getIsActive());

        // count 查询不能带 orderBy（PostgreSQL: column must appear in GROUP BY），
        // 所以先统计总数，再加排序
        long total = conceptMapper.selectCount(wrapper);
        wrapper.orderByDesc(ConceptPO::getStockCount);
        var pageParam = new Page<ConceptPO>(query.getPage(), Math.min(query.getPageSize(), 100));
        List<ConceptVO> list = ConceptConverter.toVOList(conceptMapper.selectPage(pageParam, wrapper).getRecords());
        return PageResult.of(total, list, query.getPage(), query.getPageSize());
    }

    // ── by-symbol 反查 ───────────────────────────────────────

    @Override
    public List<ConceptBriefVO> bySymbol(String symbol) {
        List<ConceptBriefVO> list = new ArrayList<>();
        for (ConceptMapper.ConceptBriefRow row : conceptMapper.selectBriefsBySymbol(symbol)) {
            ConceptBriefVO vo = new ConceptBriefVO();
            vo.setConceptId(row.getConceptId());
            vo.setName(row.getName());
            vo.setSource(row.getSource());
            vo.setConceptType(row.getConceptType());
            list.add(vo);
        }
        return list;
    }

    @Override
    public List<ConceptLiveVO> liveBySymbol(String symbol) {
        Object data = collectorService.query("stock_concepts", Map.of("symbol", symbol));
        List<ConceptLiveVO> list = new ArrayList<>();
        if (!(data instanceof List<?> rawList)) return list;
        for (Object rawItem : rawList) {
            if (!(rawItem instanceof Map<?, ?> rawMap)) continue;
            Object indexCode = rawMap.get("index_code");
            if (indexCode == null) indexCode = rawMap.get("concept_code");
            ConceptLiveVO vo = new ConceptLiveVO();
            vo.setConceptCode(indexCode == null ? null : String.valueOf(indexCode));
            vo.setName(rawMap.get("name") == null ? null : String.valueOf(rawMap.get("name")));
            vo.setSource("ths");
            vo.setReason(rawMap.get("reason") == null ? null : String.valueOf(rawMap.get("reason")));
            list.add(vo);
        }
        return list;
    }

    // ── 实时行情 ─────────────────────────────────────────────

    /** 查询股票名称，回退为代码 */
    private String queryStockName(String symbol) {
        return symbol;
    }

    /**
     * 批量取概念实时快照。
     *
     * <p>key 为 index_code。
     */
    private Map<String, ConceptSnapshotVO> quotesFor(
            List<String> indexCodes, Map<String, String> nameByCode) {
        Map<String, ConceptSnapshotVO> quotesByCode = new LinkedHashMap<>();
        for (String indexCode : indexCodes) {
            if (indexCode == null || indexCode.isBlank()) continue;
            try {
                Object data = collectorService.query("concept_minute", Map.of("index_code", indexCode));
                Map<String, Object> firstBar = firstBarOf(data);
                if (firstBar == null) continue;
                Double pctChange = numOf(firstBar.get("change_pct"));
                ConceptSnapshotVO quote = new ConceptSnapshotVO();
                quote.setIndexCode(indexCode);
                quote.setConceptName(nameByCode.getOrDefault(indexCode, ""));
                quote.setPrice(numOf(firstBar.get("price")));
                quote.setPrevClose(numOf(firstBar.get("pre_close")));
                quote.setChange(numOf(firstBar.get("change")));
                quote.setPctChange(pctChange);
                quote.setColor(resolveColor(pctChange));
                quote.setTradeTime(strOf(firstBar.get("trade_time")));
                quote.setCapturedAt(null);
                quote.setStale(false);
                quote.setRankLabel("");
                quote.setUpDownLabel("");
                quotesByCode.put(indexCode, quote);
            } catch (Exception ignored) {
                // 单个概念取不到时跳过，不影响其余
            }
        }
        return quotesByCode;
    }

    /** 从 collector 返回值中取第一根 bar */
    @SuppressWarnings("unchecked")
    private Map<String, Object> firstBarOf(Object data) {
        if (data instanceof List<?> rawList && !rawList.isEmpty() && rawList.get(0) instanceof Map)
            return (Map<String, Object>) rawList.get(0);
        if (data instanceof Map) return (Map<String, Object>) data;
        return null;
    }

    // ── 概念 Tab ─────────────────────────────────────────────

    @Override
    public ConceptTabContentVO tab(String symbol, String stockNameParam, boolean mergeLive) {
        String stockName = stockNameParam == null ? queryStockName(symbol) : stockNameParam;

        List<ConceptMapper.ConceptGroupRow> groups = conceptMapper.selectGroupsBySymbol(symbol);
        List<ConceptGroupedVO> grouped = new ArrayList<>();
        Map<String, String> nameByCode = new HashMap<>();
        List<String> codes = new ArrayList<>();
        for (ConceptMapper.ConceptGroupRow row : groups) {
            ConceptGroupedVO vo = new ConceptGroupedVO();
            vo.setConceptId(row.getConceptId());
            vo.setIndexCode(row.getIndexCode());
            vo.setName(row.getName());
            vo.setSource(row.getSource());
            vo.setConceptType(row.getConceptType());
            vo.setDescription(row.getDescription());
            vo.setReason(row.getReason());
            vo.setSnapshot(null);
            grouped.add(vo);
            nameByCode.put(row.getIndexCode(), row.getName());
            if (row.getIndexCode() != null && !row.getIndexCode().isBlank()) codes.add(row.getIndexCode());
        }

        Map<String, ConceptSnapshotVO> quotesByCode = quotesFor(codes, nameByCode);
        for (ConceptGroupedVO vo : grouped) vo.setSnapshot(quotesByCode.get(vo.getIndexCode()));

        // 按类型分桶
        Map<String, List<ConceptGroupedVO>> bucketByType = new LinkedHashMap<>();
        for (String conceptType : CONCEPT_TYPE_ORDER) bucketByType.put(conceptType, new ArrayList<>());
        for (ConceptGroupedVO vo : grouped)
            bucketByType.computeIfAbsent(vo.getConceptType(), key -> new ArrayList<>()).add(vo);

        if (mergeLive) {
            // 合并实时反查（按 name 去重）
            Set<String> existingNames = new HashSet<>();
            for (ConceptGroupedVO vo : grouped) existingNames.add(vo.getName());
            List<ConceptGroupedVO> realtimeRows = new ArrayList<>();
            for (ConceptLiveVO live : liveBySymbol(symbol)) {
                if (live.getName() == null || existingNames.contains(live.getName())) continue;
                ConceptGroupedVO vo = new ConceptGroupedVO();
                vo.setConceptId(null);
                vo.setIndexCode(live.getConceptCode());
                vo.setConceptCode(live.getConceptCode());
                vo.setName(live.getName());
                vo.setSource("ths");
                vo.setConceptType("other");
                vo.setDescription(null);
                vo.setReason(live.getReason());
                vo.setSnapshot(null);
                vo.setIsRealtime(true);
                realtimeRows.add(vo);
            }
            realtimeRows.sort(Comparator.comparing(ConceptGroupedVO::getName, Comparator.nullsFirst(String::compareTo)));
            bucketByType.computeIfAbsent("other", key -> new ArrayList<>()).addAll(0, realtimeRows);
        }

        List<ConceptTabSectionVO> sections = new ArrayList<>();
        int totalCount = 0;
        for (String conceptType : CONCEPT_TYPE_ORDER) {
            List<ConceptGroupedVO> rows = bucketByType.getOrDefault(conceptType, List.of());
            if (rows.isEmpty()) continue;
            // 按涨跌幅倒序，null 排最后；同值按名称
            rows.sort(
                    Comparator.comparing(
                                    (ConceptGroupedVO vo) -> vo.getSnapshot() == null ? null : vo.getSnapshot().getPctChange(),
                                    Comparator.nullsLast(Comparator.reverseOrder()))
                            .thenComparing(
                                    ConceptGroupedVO::getName, Comparator.nullsFirst(String::compareTo)));
            ConceptTabSectionVO section = new ConceptTabSectionVO();
            section.setType(conceptType);
            section.setTypeLabel(ConceptConverter.typeLabel(conceptType));
            section.setConcepts(rows);
            sections.add(section);
            totalCount += rows.size();
        }

        ConceptTabContentVO result = new ConceptTabContentVO();
        result.setSymbol(symbol);
        result.setStockName(stockName);
        result.setSections(sections);
        result.setTotalCount(totalCount);
        result.setIsMerged(mergeLive);
        result.setLastMergedAt(mergeLive ? OffsetDateTime.now().toString() : null);
        return result;
    }

    // ── 同步状态 ─────────────────────────────────────────────

    @Override
    public ConceptSyncStatusVO syncStatus() {
        Long activeCount =
                conceptMapper.selectCount(new LambdaQueryWrapper<ConceptPO>().eq(ConceptPO::getIsActive, true));
        ConceptSyncStatusVO result = new ConceptSyncStatusVO();
        result.setActiveConcepts(activeCount);
        result.setLastSyncedAt(conceptMapper.selectMaxSyncedAt());
        return result;
    }

    // ── 概念详情 ─────────────────────────────────────────────

    @Override
    public ConceptDetailVO detail(String conceptName) {
        ConceptPO concept =
                conceptMapper.selectOne(
                        new LambdaQueryWrapper<ConceptPO>().eq(ConceptPO::getName, conceptName));
        if (concept == null) throw new BusinessException(404, "概念不存在");

        List<ConceptDetailMemberVO> members = new ArrayList<>();
        var memberRows =
                conceptMemberMapper.selectList(
                        new LambdaQueryWrapper<com.attribution.concept.entity.ConceptMemberPO>()
                                .eq(
                                        com.attribution.concept.entity.ConceptMemberPO::getConceptId,
                                        concept.getId()));
        for (var member : memberRows) {
            ConceptDetailMemberVO memberVO = new ConceptDetailMemberVO();
            memberVO.setSymbol(member.getSymbol());
            memberVO.setReason(member.getReason());
            members.add(memberVO);
        }

        ConceptDetailVO result = new ConceptDetailVO();
        ConceptVO base = ConceptConverter.toVO(concept);
        result.setConceptId(base.getConceptId());
        result.setIndexCode(base.getIndexCode());
        result.setName(base.getName());
        result.setSource(base.getSource());
        result.setConceptType(base.getConceptType());
        result.setStockCount(base.getStockCount());
        result.setDescription(base.getDescription());
        result.setIsActive(base.getIsActive());
        result.setLastSyncedAt(base.getLastSyncedAt());
        result.setFirstSeenAt(base.getFirstSeenAt());
        result.setMembers(members);
        return result;
    }

    // ── 概念指数日 K ─────────────────────────────────────────

    @Override
    public List<ConceptKlineBarVO> indexKline(
            String conceptName, String startDate, String endDate, int limit) {
        var query = new LambdaQueryWrapper<ConceptIndexPO>().eq(ConceptIndexPO::getConceptName, conceptName);
        if (startDate != null && !startDate.isBlank())
            query.ge(ConceptIndexPO::getTradeDate, LocalDate.parse(startDate));
        if (endDate != null && !endDate.isBlank())
            query.le(ConceptIndexPO::getTradeDate, LocalDate.parse(endDate));
        query.orderByDesc(ConceptIndexPO::getTradeDate);
        List<ConceptIndexPO> rows = TopN.query(conceptIndexMapper, query, Math.min(limit, 2000));

        List<ConceptKlineBarVO> bars = new ArrayList<>();
        for (ConceptIndexPO row : rows) {
            ConceptKlineBarVO barVO = new ConceptKlineBarVO();
            barVO.setDate(String.valueOf(row.getTradeDate()));
            barVO.setOpen(row.getOpen());
            barVO.setHigh(row.getHigh());
            barVO.setLow(row.getLow());
            barVO.setClose(row.getClose());
            barVO.setVolume(row.getVolume() == null ? null : java.math.BigDecimal.valueOf(row.getVolume()));
            barVO.setAmount(row.getAmount());
            barVO.setChangePct(row.getChangePct());
            barVO.setColor(resolveColor(numOf(row.getChangePct())));
            bars.add(barVO);
        }
        return bars;
    }

    // ── 概念大盘 ─────────────────────────────────────────────

    @Override
    public PageResult<ConceptBoardItemVO> board(ConceptBoardQuery query) {
        var wrapper = new LambdaQueryWrapper<ConceptPO>();
        if (query.getTypeFilter() != null && !query.getTypeFilter().isBlank()
                && !query.getTypeFilter().equals("all"))
            wrapper.eq(ConceptPO::getConceptType, query.getTypeFilter());
        long total = conceptMapper.selectCount(wrapper);
        var pageParam = new Page<ConceptPO>(query.getPage(), Math.min(query.getPageSize(), 500));
        List<ConceptPO> rows = conceptMapper.selectPage(pageParam, wrapper).getRecords();

        List<String> codes = new ArrayList<>();
        Map<String, String> nameByCode = new HashMap<>();
        for (ConceptPO row : rows) {
            if (row.getIndexCode() == null || row.getIndexCode().isBlank()) continue;
            codes.add(row.getIndexCode());
            nameByCode.put(row.getIndexCode(), row.getName());
        }
        Map<String, ConceptSnapshotVO> quotesByCode = quotesFor(codes, nameByCode);

        List<ConceptBoardItemVO> items = new ArrayList<>();
        for (ConceptPO row : rows) {
            ConceptBoardItemVO itemVO = new ConceptBoardItemVO();
            itemVO.setConceptId(row.getId());
            itemVO.setIndexCode(row.getIndexCode());
            itemVO.setName(row.getName());
            itemVO.setSource(row.getSource());
            itemVO.setConceptType(row.getConceptType() == null ? "other" : row.getConceptType());
            itemVO.setConceptTypeLabel(ConceptConverter.typeLabel(row.getConceptType()));
            itemVO.setStockCount(row.getStockCount());
            itemVO.setDescription(row.getDescription());
            ConceptSnapshotVO quote = quotesByCode.get(row.getIndexCode());
            if (quote == null) {
                itemVO.setColor("flat");
                itemVO.setStale(false);
            } else {
                itemVO.setPrice(quote.getPrice());
                itemVO.setPrevClose(quote.getPrevClose());
                itemVO.setChange(quote.getChange());
                itemVO.setPctChange(quote.getPctChange());
                itemVO.setColor(quote.getColor());
                itemVO.setTradeTime(quote.getTradeTime());
                itemVO.setCapturedAt(quote.getCapturedAt());
                itemVO.setStale(quote.getStale());
            }
            items.add(itemVO);
        }

        // 排序（行情类排序需在拿到快照后进行）
        if ("pct_change".equals(query.getSortBy())) {
            Comparator<ConceptBoardItemVO> byPct =
                    Comparator.comparing(
                                    (ConceptBoardItemVO item) -> item.getPctChange(),
                                    Comparator.nullsLast(Comparator.reverseOrder()))
                            .thenComparing(
                                    ConceptBoardItemVO::getName, Comparator.nullsFirst(String::compareTo));
            if ("asc".equals(query.getSortOrder()))
                byPct =
                        Comparator.comparing(
                                        (ConceptBoardItemVO item) -> item.getPctChange(),
                                        Comparator.nullsLast(Comparator.naturalOrder()))
                                .thenComparing(
                                        ConceptBoardItemVO::getName,
                                        Comparator.nullsFirst(String::compareTo));
            items.sort(byPct);
        } else if ("stock_count".equals(query.getSortBy())) {
            Comparator<ConceptBoardItemVO> byCount =
                    Comparator.comparing(
                                    (ConceptBoardItemVO item) ->
                                            item.getStockCount() == null ? 0 : item.getStockCount(),
                                    Comparator.reverseOrder())
                            .thenComparing(
                                    ConceptBoardItemVO::getName, Comparator.nullsFirst(String::compareTo));
            if ("asc".equals(query.getSortOrder()))
                byCount =
                        Comparator.comparing(
                                        (ConceptBoardItemVO item) ->
                                                item.getStockCount() == null ? 0 : item.getStockCount(),
                                        Comparator.naturalOrder())
                                .thenComparing(
                                        ConceptBoardItemVO::getName,
                                        Comparator.nullsFirst(String::compareTo));
            items.sort(byCount);
        } else if ("name".equals(query.getSortBy())) {
            Comparator<ConceptBoardItemVO> byName =
                    Comparator.comparing(
                            ConceptBoardItemVO::getName, Comparator.nullsFirst(String::compareTo));
            if ("desc".equals(query.getSortOrder())) byName = byName.reversed();
            items.sort(byName);
        }
        return PageResult.of(total, items, query.getPage(), query.getPageSize());
    }

    // ── 概念成员 ─────────────────────────────────────────────

    @Override
    public PageResult<ConceptMemberItemVO> members(ConceptMemberQuery query) {
        long total = conceptMapper.countMembers(query.getConceptId());
        int effectiveSize = Math.min(query.getPageSize(), 200);
        int offset = Math.max(query.getPage() - 1, 0) * effectiveSize;

        List<ConceptMapper.ConceptMemberRow> rows =
                conceptMapper.selectMemberRows(query.getConceptId(), effectiveSize, offset);

        List<String> symbols = rows.stream().map(ConceptMapper.ConceptMemberRow::getSymbol).toList();
        Map<String, List<PoolMembershipVO>> poolsBySymbol = new HashMap<>();
        if (query.isWithPools() && !symbols.isEmpty())
            for (ConceptMemberMapper.PoolMembershipRow row :
                    conceptMemberMapper.selectPoolMemberships(symbols)) {
                PoolMembershipVO poolVO = new PoolMembershipVO();
                poolVO.setPoolId(row.getPoolId());
                poolVO.setName(row.getName());
                poolVO.setPoolType(row.getPoolType());
                poolVO.setJoinedAt(null);
                poolsBySymbol.computeIfAbsent(row.getSymbol(), key -> new ArrayList<>()).add(poolVO);
            }

        List<ConceptMemberItemVO> items = new ArrayList<>();
        for (ConceptMapper.ConceptMemberRow row : rows) {
            ConceptMemberItemVO itemVO = new ConceptMemberItemVO();
            itemVO.setSymbol(row.getSymbol());
            itemVO.setName(row.getName());
            itemVO.setIndustry(row.getIndustry());
            itemVO.setMarket(row.getMarket());
            itemVO.setLatestClose(row.getLatestClose());
            itemVO.setTotalMv(row.getTotalMv());
            itemVO.setPeTtm(row.getPeTtm());
            itemVO.setPctChange(null);
            itemVO.setColor("flat");
            itemVO.setPools(poolsBySymbol.getOrDefault(row.getSymbol(), List.of()));
            items.add(itemVO);
        }

        // 排序（行情类字段需在装配后进行）
        if ("latest_close".equals(query.getSortBy())) {
            Comparator<ConceptMemberItemVO> byClose =
                    Comparator.comparing(
                                    (ConceptMemberItemVO item) ->
                                            item.getLatestClose() == null
                                                    ? null
                                                    : item.getLatestClose().doubleValue(),
                                    Comparator.nullsLast(Comparator.reverseOrder()))
                            .thenComparing(
                                    ConceptMemberItemVO::getSymbol,
                                    Comparator.nullsFirst(String::compareTo));
            if ("asc".equals(query.getSortOrder()))
                byClose =
                        Comparator.comparing(
                                        (ConceptMemberItemVO item) ->
                                                item.getLatestClose() == null
                                                        ? null
                                                        : item.getLatestClose().doubleValue(),
                                        Comparator.nullsLast(Comparator.naturalOrder()))
                                .thenComparing(
                                        ConceptMemberItemVO::getSymbol,
                                        Comparator.nullsFirst(String::compareTo));
            items.sort(byClose);
        } else if ("total_mv".equals(query.getSortBy())) {
            Comparator<ConceptMemberItemVO> byMv =
                    Comparator.comparing(
                                    (ConceptMemberItemVO item) ->
                                            item.getTotalMv() == null ? null : item.getTotalMv().doubleValue(),
                                    Comparator.nullsLast(Comparator.reverseOrder()))
                            .thenComparing(
                                    ConceptMemberItemVO::getSymbol,
                                    Comparator.nullsFirst(String::compareTo));
            if ("asc".equals(query.getSortOrder()))
                byMv =
                        Comparator.comparing(
                                        (ConceptMemberItemVO item) ->
                                                item.getTotalMv() == null
                                                        ? null
                                                        : item.getTotalMv().doubleValue(),
                                        Comparator.nullsLast(Comparator.naturalOrder()))
                                .thenComparing(
                                        ConceptMemberItemVO::getSymbol,
                                        Comparator.nullsFirst(String::compareTo));
            items.sort(byMv);
        } else if ("name".equals(query.getSortBy())) {
            Comparator<ConceptMemberItemVO> byName =
                    Comparator.comparing(
                            ConceptMemberItemVO::getName, Comparator.nullsFirst(String::compareTo));
            if ("desc".equals(query.getSortOrder())) byName = byName.reversed();
            items.sort(byName);
        }
        return PageResult.of(total, items, query.getPage(), query.getPageSize());
    }

    // ── 概念 K 线 ─────────────────────────────────────────────

    @Override
    public ConceptKlineResponseVO conceptKline(String indexCode, ConceptKlineQuery query) {
        var wrapper = new LambdaQueryWrapper<ConceptIndexPO>().eq(ConceptIndexPO::getIndexCode, indexCode);
        if (query.getStartDate() != null && !query.getStartDate().isBlank())
            wrapper.ge(ConceptIndexPO::getTradeDate, LocalDate.parse(query.getStartDate()));
        if (query.getEndDate() != null && !query.getEndDate().isBlank())
            wrapper.le(ConceptIndexPO::getTradeDate, LocalDate.parse(query.getEndDate()));
        wrapper.orderByAsc(ConceptIndexPO::getTradeDate);
        List<ConceptIndexPO> rows = TopN.query(conceptIndexMapper, wrapper, Math.min(query.getDays(), 1500));

        List<ConceptKlineBarVO> bars = new ArrayList<>();
        for (ConceptIndexPO row : rows) {
            ConceptKlineBarVO barVO = new ConceptKlineBarVO();
            barVO.setDate(String.valueOf(row.getTradeDate()));
            barVO.setOpen(row.getOpen());
            barVO.setHigh(row.getHigh());
            barVO.setLow(row.getLow());
            barVO.setClose(row.getClose());
            barVO.setVolume(row.getVolume() == null ? null : java.math.BigDecimal.valueOf(row.getVolume()));
            barVO.setAmount(row.getAmount());
            barVO.setChangePct(row.getChangePct());
            barVO.setColor(resolveColor(numOf(row.getChangePct())));
            bars.add(barVO);
        }

        // 实时行情
        ConceptSnapshotVO realtime = null;
        try {
            Object data = collectorService.query("concept_minute", Map.of("index_code", indexCode));
            Map<String, Object> firstBar = firstBarOf(data);
            if (firstBar != null) {
                realtime = new ConceptSnapshotVO();
                realtime.setIndexCode(indexCode);
                Object conceptName = firstBar.get("concept_name");
                if (conceptName == null) conceptName = firstBar.get("name");
                realtime.setConceptName(conceptName == null ? null : String.valueOf(conceptName));
                realtime.setPrice(numOf(firstBar.get("price")));
                realtime.setPrevClose(numOf(firstBar.get("pre_close")));
                realtime.setChange(numOf(firstBar.get("change")));
                realtime.setPctChange(numOf(firstBar.get("change_pct")));
                realtime.setColor(resolveColor(realtime.getPctChange()));
                realtime.setTradeTime(strOf(firstBar.get("trade_time")));
                realtime.setCapturedAt(null);
                realtime.setStale(false);
            }
        } catch (Exception ignored) {
            // 实时不可用时回退到日 K 收盘
        }

        ConceptPO entity = null;
        try {
            entity =
                    conceptMapper.selectOne(
                            new LambdaQueryWrapper<ConceptPO>().eq(ConceptPO::getIndexCode, indexCode));
        } catch (Exception ignored) {
            // 查不到元信息不影响 K 线返回
        }

        ConceptKlineMetaVO meta = null;
        if (entity != null) {
            meta = new ConceptKlineMetaVO();
            meta.setConceptId(entity.getId());
            meta.setIndexCode(entity.getIndexCode());
            meta.setName(entity.getName());
            meta.setConceptType(entity.getConceptType());
            meta.setConceptTypeLabel(ConceptConverter.typeLabel(entity.getConceptType()));
            meta.setStockCount(entity.getStockCount());
            meta.setDescription(entity.getDescription());
            meta.setSource(entity.getSource());
        }

        if (realtime == null && !bars.isEmpty() && entity != null) {
            ConceptKlineBarVO lastBar = bars.get(bars.size() - 1);
            realtime = new ConceptSnapshotVO();
            realtime.setIndexCode(indexCode);
            realtime.setConceptName(entity.getName());
            realtime.setPrice(lastBar.getClose() == null ? null : lastBar.getClose().doubleValue());
            realtime.setPrevClose(null);
            realtime.setChange(null);
            realtime.setPctChange(
                    lastBar.getChangePct() == null ? null : lastBar.getChangePct().doubleValue());
            realtime.setColor(lastBar.getColor());
            realtime.setTradeTime(lastBar.getDate());
            realtime.setCapturedAt(null);
            realtime.setStale(true);
        }

        ConceptDataRangeVO dataRange = new ConceptDataRangeVO();
        dataRange.setStart(bars.isEmpty() ? null : bars.get(0).getDate());
        dataRange.setEnd(bars.isEmpty() ? null : bars.get(bars.size() - 1).getDate());
        dataRange.setBarsCount(bars.size());

        ConceptKlineResponseVO result = new ConceptKlineResponseVO();
        result.setKline(bars);
        result.setRealtime(realtime);
        result.setMeta(meta);
        result.setDataRange(dataRange);
        return result;
    }

    // ── 批量行情 ─────────────────────────────────────────────

    @Override
    public Map<String, ConceptSnapshotVO> quotes(List<String> codes) {
        Map<String, String> nameByCode = new HashMap<>();
        try {
            for (String code : codes) {
                ConceptPO concept =
                        conceptMapper.selectOne(
                                new LambdaQueryWrapper<ConceptPO>().eq(ConceptPO::getIndexCode, code));
                if (concept != null) nameByCode.put(code, concept.getName());
            }
        } catch (Exception ignored) {
            // 取不到名称时使用空名
        }
        return quotesFor(codes, nameByCode);
    }

    // ── 分时 ─────────────────────────────────────────────────

    @Override
    public ConceptMinuteVO minute(String indexCode) {
        if (indexCode == null || !indexCode.matches("\\d{6}"))
            throw new BusinessException(400, "index_code 需为 6 位同花顺指数编码（885xxx）");
        Object data;
        try {
            data = collectorService.query("concept_minute", Map.of("index_code", indexCode));
        } catch (Exception e) {
            throw new BusinessException(502, "概念实时行情获取失败");
        }
        Map<String, Object> firstBar = firstBarOf(data);
        if (firstBar == null) throw new BusinessException(502, "概念实时行情获取失败");

        ConceptMinuteVO result = new ConceptMinuteVO();
        result.setIndexCode(indexCode);
        Object conceptName = firstBar.get("concept_name");
        if (conceptName == null) conceptName = firstBar.get("name");
        result.setConceptName(conceptName == null ? null : String.valueOf(conceptName));
        result.setPrice(numOf(firstBar.get("price")));
        result.setPreClose(numOf(firstBar.get("pre_close")));
        result.setChange(numOf(firstBar.get("change")));
        result.setChangePct(numOf(firstBar.get("change_pct")));
        result.setTradeTime(strOf(firstBar.get("trade_time")));
        result.setCapturedAt(strOf(firstBar.get("captured_at")));
        result.setStale(false);
        result.setCached(false);
        result.setFetchedAt(null);
        return result;
    }

    // ── 工具 ─────────────────────────────────────────────────

    /** 涨跌幅 → 颜色 */
    private String resolveColor(Double pctChange) {
        if (pctChange == null) return "flat";
        return pctChange > 0 ? "up" : (pctChange < 0 ? "down" : "flat");
    }

    private Double numOf(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(value));
        } catch (Exception e) {
            return null;
        }
    }

    private String strOf(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
