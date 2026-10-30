package com.attribution.market.service.impl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.springframework.stereotype.Service;

import com.attribution.common.exception.BusinessException;
import com.attribution.common.mybatis.TopN;
import com.attribution.common.response.PageResult;
import com.attribution.market.converter.DataBoardConverter;
import com.attribution.market.converter.MarketConverter;
import com.attribution.market.dto.StockListQuery;
import com.attribution.market.entity.*;
import com.attribution.market.mapper.*;
import com.attribution.market.service.DataBoardService;
import com.attribution.market.util.IndicatorUtil;
import com.attribution.market.vo.*;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class DataBoardServiceImpl implements DataBoardService {
    private final TechKlineMapper techKlineMapper;
    private final StockInfoMapper stockInfoMapper;
    private final AdjFactorMapper adjFactorMapper;
    private final SuspendMapper suspendMapper;
    private final NameChangeMapper nameChangeMapper;
    private final MoneyflowMapper moneyflowMapper;
    private final MarginDetailMapper marginDetailMapper;
    private final TopListMapper topListMapper;
    private final TopInstMapper topInstMapper;
    private final BlockTradeMapper blockTradeMapper;
    private final HolderNumMapper holderNumMapper;
    private final DailyBasicMapper dailyBasicMapper;
    private final FinReportMapper finReportMapper;
    private final Top10HolderMapper top10HolderMapper;
    private final Top10FloatMapper top10FloatMapper;
    private final DividendMapper dividendMapper;

    /** 历史数据面默认取回条数上限 */
    private static final int HISTORY_LIMIT = 500;

    /** 技术指标递推所需的 warmup 根数 */
    private static final int WARMUP = 120;

    // ── 技术面 ───────────────────────────────────────────────

    @Override
    public TechKlineVO techKline(String symbol, int limit) {
        var query =
                new LambdaQueryWrapper<TechKlinePO>()
                        .eq(TechKlinePO::getSymbol, symbol)
                        .orderByAsc(TechKlinePO::getDate);
        List<TechKlinePO> rows = TopN.query(techKlineMapper, query, Math.min(limit, 3650));

        // warmup 前 120 根，用于指标递推
        List<TechKlinePO> warmupRows = List.of();
        if (!rows.isEmpty()) {
            var warmupQuery =
                    new LambdaQueryWrapper<TechKlinePO>()
                            .eq(TechKlinePO::getSymbol, symbol)
                            .lt(TechKlinePO::getDate, rows.get(0).getDate())
                            .orderByDesc(TechKlinePO::getDate);
            List<TechKlinePO> warmupDesc = TopN.query(techKlineMapper, warmupQuery, WARMUP);
            warmupRows = new ArrayList<>(warmupDesc);
            Collections.reverse(warmupRows);
        }
        List<TechKlinePO> allRows = new ArrayList<>(warmupRows);
        allRows.addAll(rows);
        int rowCount = allRows.size();
        double[] closePrices = new double[rowCount];
        double[] highPrices = new double[rowCount];
        double[] lowPrices = new double[rowCount];
        for (int i = 0; i < rowCount; i++) {
            closePrices[i] = IndicatorUtil.d(allRows.get(i).getClose());
            highPrices[i] = IndicatorUtil.d(allRows.get(i).getHigh());
            lowPrices[i] = IndicatorUtil.d(allRows.get(i).getLow());
        }
        var indicators = IndicatorUtil.calculate(closePrices, highPrices, lowPrices);

        List<MarketKlineVO> klines = new ArrayList<>();
        for (int i = warmupRows.size(); i < rowCount; i++) {
            TechKlinePO row = allRows.get(i);
            MarketKlineVO barVO = new MarketKlineVO();
            barVO.setTradeDate(String.valueOf(row.getDate()));
            barVO.setOpen(row.getOpen());
            barVO.setHigh(row.getHigh());
            barVO.setLow(row.getLow());
            barVO.setClose(row.getClose());
            barVO.setVolume(row.getVolume());
            barVO.setAmount(row.getAmount());
            barVO.setChangePct(row.getChangePct());
            applyIndicators(barVO, indicators.get(i));
            klines.add(barVO);
        }

        TechKlineVO result = new TechKlineVO();
        result.setSymbol(symbol);
        result.setKlines(klines);
        return result;
    }

    /** 填充 17 个技术指标列，缺失时置 null */
    private void applyIndicators(MarketKlineVO vo, java.util.Map<String, Double> indicators) {
        vo.setMa5(indicators.get("ma5"));
        vo.setMa10(indicators.get("ma10"));
        vo.setMa20(indicators.get("ma20"));
        vo.setMa60(indicators.get("ma60"));
        vo.setEma12(indicators.get("ema12"));
        vo.setEma26(indicators.get("ema26"));
        vo.setMacdDif(indicators.get("macd_dif"));
        vo.setMacdDea(indicators.get("macd_dea"));
        vo.setMacdBar(indicators.get("macd_bar"));
        vo.setRsi6(indicators.get("rsi6"));
        vo.setRsi12(indicators.get("rsi12"));
        vo.setRsi24(indicators.get("rsi24"));
        vo.setKdjK(indicators.get("kdj_k"));
        vo.setKdjD(indicators.get("kdj_d"));
        vo.setKdjJ(indicators.get("kdj_j"));
        vo.setBollUp(indicators.get("boll_up"));
        vo.setBollMid(indicators.get("boll_mid"));
        vo.setBollDn(indicators.get("boll_dn"));
    }

    // ── 各数据面：按 symbol 取最近 N 行 ──────────────────────

    @Override
    public AdjFactorResponseVO adjFactor(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<AdjFactorPO>()
                        .eq(AdjFactorPO::getSymbol, symbol)
                        .orderByDesc(AdjFactorPO::getTradeDate);
        List<AdjFactorPO> rows = TopN.query(adjFactorMapper, wrapper, HISTORY_LIMIT);
        AdjFactorResponseVO result = new AdjFactorResponseVO();
        result.setSymbol(symbol);
        result.setFactors(DataBoardConverter.toAdjFactorList(rows));
        return result;
    }

    @Override
    public SuspendResponseVO suspend(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<SuspendPO>()
                        .eq(SuspendPO::getSymbol, symbol)
                        .orderByDesc(SuspendPO::getTradeDate);
        List<SuspendPO> rows = TopN.query(suspendMapper, wrapper, HISTORY_LIMIT);
        SuspendResponseVO result = new SuspendResponseVO();
        result.setSymbol(symbol);
        result.setEvents(DataBoardConverter.toSuspendList(rows));
        return result;
    }

    @Override
    public NameChangeResponseVO nameChange(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<NameChangePO>()
                        .eq(NameChangePO::getSymbol, symbol)
                        .orderByDesc(NameChangePO::getStartDate);
        List<NameChangePO> rows = TopN.query(nameChangeMapper, wrapper, HISTORY_LIMIT);
        NameChangeResponseVO result = new NameChangeResponseVO();
        result.setSymbol(symbol);
        result.setHistory(DataBoardConverter.toNameChangeList(rows));
        return result;
    }

    @Override
    public MoneyflowResponseVO moneyflow(String symbol, int days) {
        int limit = Math.min(Math.max(days, 1), HISTORY_LIMIT);
        var wrapper =
                new LambdaQueryWrapper<MoneyflowPO>()
                        .eq(MoneyflowPO::getSymbol, symbol)
                        .orderByDesc(MoneyflowPO::getTradeDate);
        List<MoneyflowPO> rows = TopN.query(moneyflowMapper, wrapper, limit);
        MoneyflowResponseVO result = new MoneyflowResponseVO();
        result.setSymbol(symbol);
        result.setDays(limit);
        result.setFlows(DataBoardConverter.toMoneyflowList(rows));
        return result;
    }

    @Override
    public MarginResponseVO margin(String symbol, int days) {
        int limit = Math.min(Math.max(days, 1), HISTORY_LIMIT);
        var wrapper =
                new LambdaQueryWrapper<MarginDetailPO>()
                        .eq(MarginDetailPO::getSymbol, symbol)
                        .orderByDesc(MarginDetailPO::getTradeDate);
        List<MarginDetailPO> rows = TopN.query(marginDetailMapper, wrapper, limit);
        MarginResponseVO result = new MarginResponseVO();
        result.setSymbol(symbol);
        result.setDays(limit);
        result.setDetails(DataBoardConverter.toMarginList(rows));
        return result;
    }

    @Override
    public TopListResponseVO topList(String symbol, int days) {
        int limit = Math.min(Math.max(days, 1), HISTORY_LIMIT);
        var wrapper =
                new LambdaQueryWrapper<TopListPO>()
                        .eq(TopListPO::getSymbol, symbol)
                        .orderByDesc(TopListPO::getTradeDate);
        List<TopListPO> rows = TopN.query(topListMapper, wrapper, limit);
        TopListResponseVO result = new TopListResponseVO();
        result.setSymbol(symbol);
        result.setDays(limit);
        result.setLists(DataBoardConverter.toTopListList(rows));
        return result;
    }

    @Override
    public TopInstResponseVO topInst(String symbol, int days) {
        int limit = Math.min(Math.max(days, 1), HISTORY_LIMIT);
        var wrapper =
                new LambdaQueryWrapper<TopInstPO>()
                        .eq(TopInstPO::getSymbol, symbol)
                        .orderByDesc(TopInstPO::getTradeDate);
        List<TopInstPO> rows = TopN.query(topInstMapper, wrapper, limit);
        TopInstResponseVO result = new TopInstResponseVO();
        result.setSymbol(symbol);
        result.setDays(limit);
        result.setDetails(DataBoardConverter.toTopInstList(rows));
        return result;
    }

    @Override
    public BlockTradeResponseVO blockTrade(String symbol, int days) {
        int limit = Math.min(Math.max(days, 1), HISTORY_LIMIT);
        var wrapper =
                new LambdaQueryWrapper<BlockTradePO>()
                        .eq(BlockTradePO::getSymbol, symbol)
                        .orderByDesc(BlockTradePO::getTradeDate);
        List<BlockTradePO> rows = TopN.query(blockTradeMapper, wrapper, limit);
        BlockTradeResponseVO result = new BlockTradeResponseVO();
        result.setSymbol(symbol);
        result.setDays(limit);
        result.setTrades(DataBoardConverter.toBlockTradeList(rows));
        return result;
    }

    @Override
    public HolderNumResponseVO holderNum(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<HolderNumPO>()
                        .eq(HolderNumPO::getSymbol, symbol)
                        .orderByDesc(HolderNumPO::getEndDate);
        List<HolderNumPO> rows = TopN.query(holderNumMapper, wrapper, HISTORY_LIMIT);
        HolderNumResponseVO result = new HolderNumResponseVO();
        result.setSymbol(symbol);
        result.setHistory(DataBoardConverter.toHolderNumList(rows));
        return result;
    }

    @Override
    public StockInfoVO stockInfo(String symbol) {
        StockInfoPO stockInfo =
                stockInfoMapper.selectOne(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (stockInfo == null) throw new BusinessException(404, "股票 " + symbol + " 不存在");
        return MarketConverter.toStockInfoVO(stockInfo);
    }

    @Override
    public ValuationResponseVO dailyBasic(String symbol, int days) {
        int limit = Math.min(Math.max(days, 1), HISTORY_LIMIT);
        var wrapper =
                new LambdaQueryWrapper<DailyBasicPO>()
                        .eq(DailyBasicPO::getSymbol, symbol)
                        .orderByDesc(DailyBasicPO::getTradeDate);
        List<DailyBasicPO> rows = TopN.query(dailyBasicMapper, wrapper, limit);
        ValuationResponseVO result = new ValuationResponseVO();
        result.setSymbol(symbol);
        result.setDays(limit);
        result.setValuation(DataBoardConverter.toValuationList(rows));
        return result;
    }

    @Override
    public FinReportResponseVO finReport(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<FinReportPO>()
                        .eq(FinReportPO::getSymbol, symbol)
                        .orderByDesc(FinReportPO::getEndDate);
        List<FinReportPO> rows = TopN.query(finReportMapper, wrapper, HISTORY_LIMIT);
        FinReportResponseVO result = new FinReportResponseVO();
        result.setSymbol(symbol);
        result.setReports(DataBoardConverter.toFinReportList(rows));
        return result;
    }

    @Override
    public Top10HolderResponseVO top10Holders(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<Top10HolderPO>()
                        .eq(Top10HolderPO::getSymbol, symbol)
                        .orderByDesc(Top10HolderPO::getEndDate);
        List<Top10HolderPO> rows = TopN.query(top10HolderMapper, wrapper, HISTORY_LIMIT);
        Top10HolderResponseVO result = new Top10HolderResponseVO();
        result.setSymbol(symbol);
        result.setHolders(DataBoardConverter.toTop10HolderList(rows));
        return result;
    }

    @Override
    public Top10FloatResponseVO top10Float(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<Top10FloatPO>()
                        .eq(Top10FloatPO::getSymbol, symbol)
                        .orderByDesc(Top10FloatPO::getEndDate);
        List<Top10FloatPO> rows = TopN.query(top10FloatMapper, wrapper, HISTORY_LIMIT);
        Top10FloatResponseVO result = new Top10FloatResponseVO();
        result.setSymbol(symbol);
        result.setHolders(DataBoardConverter.toTop10FloatList(rows));
        return result;
    }

    @Override
    public DividendResponseVO dividend(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<DividendPO>()
                        .eq(DividendPO::getSymbol, symbol)
                        .orderByDesc(DividendPO::getEndDate);
        List<DividendPO> rows = TopN.query(dividendMapper, wrapper, HISTORY_LIMIT);
        DividendResponseVO result = new DividendResponseVO();
        result.setSymbol(symbol);
        result.setDividends(DataBoardConverter.toDividendList(rows));
        return result;
    }

    // ── 总览 ─────────────────────────────────────────────────

    @Override
    public OverviewVO overview(String symbol) {
        OverviewVO result = new OverviewVO();
        result.setSymbol(symbol);

        StockInfoPO stockInfo =
                stockInfoMapper.selectOne(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (stockInfo != null) {
            OverviewStockVO stockVO = new OverviewStockVO();
            stockVO.setName(stockInfo.getName());
            stockVO.setIndustry(stockInfo.getIndustry());
            stockVO.setListDate(MarketConverter.formatListDate(stockInfo.getListDate()));
            result.setStock(stockVO);
        }

        OverviewTechVO techVO = new OverviewTechVO();
        techVO.setKlineCount(countTechKline(symbol));
        techVO.setKlineLatestDate(latestKlineDate(symbol));
        result.setTech(techVO);

        OverviewFundamentalVO fundamentalVO = new OverviewFundamentalVO();
        var valuationWrapper =
                new LambdaQueryWrapper<DailyBasicPO>()
                        .eq(DailyBasicPO::getSymbol, symbol)
                        .orderByDesc(DailyBasicPO::getTradeDate);
        List<DailyBasicPO> valuationRows = TopN.latest(dailyBasicMapper, valuationWrapper);
        if (!valuationRows.isEmpty()) {
            DailyBasicPO latest = valuationRows.get(0);
            fundamentalVO.setLatestClose(latest.getClose());
            fundamentalVO.setLatestPe(latest.getPe());
            fundamentalVO.setLatestPb(latest.getPb());
            fundamentalVO.setLatestTotalMv(latest.getTotalMv());
            fundamentalVO.setLatestDate(String.valueOf(latest.getTradeDate()));
        }
        result.setFundamental(fundamentalVO);

        OverviewCapitalVO capitalVO = new OverviewCapitalVO();
        capitalVO.setMoneyflowLatestDate(latestMoneyflowDate(symbol));
        capitalVO.setMoneyflowCount(countMoneyflow(symbol));
        capitalVO.setMarginLatestDate(latestMarginDate(symbol));
        capitalVO.setMarginCount(countMargin(symbol));
        capitalVO.setTopListCount(countTopList(symbol));
        capitalVO.setHolderCount(countHolderNum(symbol));
        result.setCapital(capitalVO);

        OverviewNewsVO newsVO = new OverviewNewsVO();
        newsVO.setAvailable(false);
        newsVO.setMessage("news_article 任务等待 tushare news 权限开通");
        result.setNews(newsVO);

        return result;
    }

    private long countTechKline(String symbol) {
        return techKlineMapper.selectCount(
                new LambdaQueryWrapper<TechKlinePO>().eq(TechKlinePO::getSymbol, symbol));
    }

    private long countMoneyflow(String symbol) {
        return moneyflowMapper.selectCount(
                new LambdaQueryWrapper<MoneyflowPO>().eq(MoneyflowPO::getSymbol, symbol));
    }

    private long countMargin(String symbol) {
        return marginDetailMapper.selectCount(
                new LambdaQueryWrapper<MarginDetailPO>().eq(MarginDetailPO::getSymbol, symbol));
    }

    private long countTopList(String symbol) {
        return topListMapper.selectCount(
                new LambdaQueryWrapper<TopListPO>().eq(TopListPO::getSymbol, symbol));
    }

    private long countHolderNum(String symbol) {
        return holderNumMapper.selectCount(
                new LambdaQueryWrapper<HolderNumPO>().eq(HolderNumPO::getSymbol, symbol));
    }

    private String latestMoneyflowDate(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<MoneyflowPO>()
                        .eq(MoneyflowPO::getSymbol, symbol)
                        .orderByDesc(MoneyflowPO::getTradeDate);
        List<MoneyflowPO> rows = TopN.latest(moneyflowMapper, wrapper);
        return rows.isEmpty() ? null : String.valueOf(rows.get(0).getTradeDate());
    }

    private String latestMarginDate(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<MarginDetailPO>()
                        .eq(MarginDetailPO::getSymbol, symbol)
                        .orderByDesc(MarginDetailPO::getTradeDate);
        List<MarginDetailPO> rows = TopN.latest(marginDetailMapper, wrapper);
        return rows.isEmpty() ? null : String.valueOf(rows.get(0).getTradeDate());
    }

    /** K 线最晚日期 */
    private String latestKlineDate(String symbol) {
        var wrapper =
                new LambdaQueryWrapper<TechKlinePO>()
                        .eq(TechKlinePO::getSymbol, symbol)
                        .orderByDesc(TechKlinePO::getDate);
        List<TechKlinePO> rows = TopN.latest(techKlineMapper, wrapper);
        return rows.isEmpty() ? null : String.valueOf(rows.get(0).getDate());
    }

    // ── 左侧股票列 ───────────────────────────────────────────

    @Override
    public PageResult<StockListItemVO> stockList(StockListQuery query) {
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
        if (query.getListStatus() != null && !query.getListStatus().isBlank())
            wrapper.eq(StockInfoPO::getListStatus, query.getListStatus());
        // count 查询不能带 orderBy（PostgreSQL: column must appear in GROUP BY），
        // 所以先统计总数，再加排序
        long total = stockInfoMapper.selectCount(wrapper);
        wrapper.orderByAsc(StockInfoPO::getSymbol);
        var pageParam = new Page<StockInfoPO>(query.getPage(), query.getPageSize());
        List<StockInfoPO> records = stockInfoMapper.selectPage(pageParam, wrapper).getRecords();

        List<StockListItemVO> list = new ArrayList<>();
        for (StockInfoPO row : records) list.add(MarketConverter.toStockListItemVO(row));
        return PageResult.of(total, list, query.getPage(), query.getPageSize());
    }

    @Override
    public PageResult<StockListItemVO> stockListAll() {
        var wrapper =
                new LambdaQueryWrapper<StockInfoPO>()
                        .select(
                                StockInfoPO::getSymbol,
                                StockInfoPO::getName,
                                StockInfoPO::getIndustry,
                                StockInfoPO::getMarket,
                                StockInfoPO::getExchange,
                                StockInfoPO::getListStatus)
                        .eq(StockInfoPO::getListStatus, "L")
                        .orderByAsc(StockInfoPO::getSymbol);
        List<StockInfoPO> records = TopN.query(stockInfoMapper, wrapper, 10000);
        List<StockListItemVO> list = new ArrayList<>();
        for (StockInfoPO row : records) list.add(MarketConverter.toStockListItemVO(row));
        // 全量接口：一次性返回，单页承载全部数据
        return PageResult.of(list.size(), list, 1, Math.max(list.size(), 1));
    }

    // ── 归因分析 ─────────────────────────────────────────────

    @Override
    public StockAnalysisVO analysis(String symbol, int days) {
        StockInfoPO stockInfo =
                stockInfoMapper.selectOne(
                        new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
        if (stockInfo == null) throw new BusinessException(404, "股票不存在");

        // 取近 days+120 根升序 K 线
        var query =
                new LambdaQueryWrapper<TechKlinePO>()
                        .eq(TechKlinePO::getSymbol, symbol)
                        .orderByDesc(TechKlinePO::getDate);
        List<TechKlinePO> descRows = TopN.query(techKlineMapper, query, Math.min(days + WARMUP, 2000));
        if (descRows.isEmpty())
            throw new BusinessException(400, "暂无 K 线数据, 请先采集（days=" + days + "）");
        List<TechKlinePO> ascRows = new ArrayList<>(descRows);
        Collections.reverse(ascRows);

        int rowCount = ascRows.size();
        double[] closePrices = new double[rowCount];
        double[] highPrices = new double[rowCount];
        double[] lowPrices = new double[rowCount];
        for (int i = 0; i < rowCount; i++) {
            closePrices[i] = IndicatorUtil.d(ascRows.get(i).getClose());
            highPrices[i] = IndicatorUtil.d(ascRows.get(i).getHigh());
            lowPrices[i] = IndicatorUtil.d(ascRows.get(i).getLow());
        }
        var indicators = IndicatorUtil.calculate(closePrices, highPrices, lowPrices);
        int fromIndex = Math.max(0, rowCount - days);
        List<KlineVO> klines = new ArrayList<>();
        for (int i = fromIndex; i < rowCount; i++) {
            TechKlinePO row = ascRows.get(i);
            klines.add(MarketConverter.toKlineVO(row, stockInfo.getName(), indicators.get(i)));
        }

        // summary 基于全量（含 warmup）
        Double[] changes = new Double[rowCount];
        for (int i = 0; i < rowCount; i++) changes[i] = IndicatorUtil.num(ascRows.get(i).getChangePct());
        var summaryMap = IndicatorUtil.summarize(closePrices, changes, indicators);

        StockAnalysisVO result = new StockAnalysisVO();
        result.setStock(MarketConverter.toAnalysisStockVO(stockInfo));
        result.setSummary(MarketConverter.toSummaryVO(summaryMap));
        result.setKlines(klines);
        result.setPools(List.of());
        return result;
    }
}
