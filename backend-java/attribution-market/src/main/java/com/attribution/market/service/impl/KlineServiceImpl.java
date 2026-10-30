package com.attribution.market.service.impl;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import org.springframework.stereotype.Service;

import com.attribution.common.exception.BusinessException;
import com.attribution.common.mybatis.TopN;
import com.attribution.common.response.PageResult;
import com.attribution.market.converter.MarketConverter;
import com.attribution.market.dto.KlineQuery;
import com.attribution.market.entity.StockInfoPO;
import com.attribution.market.entity.TechKlinePO;
import com.attribution.market.mapper.StockInfoMapper;
import com.attribution.market.mapper.TechKlineMapper;
import com.attribution.market.service.KlineService;
import com.attribution.market.util.IndicatorUtil;
import com.attribution.market.vo.KlineDeleteVO;
import com.attribution.market.vo.KlineStatsVO;
import com.attribution.market.vo.KlineVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class KlineServiceImpl implements KlineService {
    private final TechKlineMapper techKlineMapper;
    private final StockInfoMapper stockInfoMapper;

    /** 取股票名称，查不到时回退为代码 */
    private String queryStockName(String symbol) {
        try {
            StockInfoPO stock =
                    stockInfoMapper.selectOne(
                            new LambdaQueryWrapper<StockInfoPO>().eq(StockInfoPO::getSymbol, symbol));
            return stock == null ? symbol : String.valueOf(stock.getName());
        } catch (Exception e) {
            return symbol;
        }
    }

    /** 取升序全量 K 线 */
    private List<TechKlinePO> loadAsc(String symbol, LocalDate start, LocalDate end, int limit) {
        var wrapper = new LambdaQueryWrapper<TechKlinePO>().eq(TechKlinePO::getSymbol, symbol);
        if (start != null) wrapper.ge(TechKlinePO::getDate, start);
        if (end != null) wrapper.le(TechKlinePO::getDate, end);
        wrapper.orderByAsc(TechKlinePO::getDate);
        return TopN.query(techKlineMapper, wrapper, Math.min(limit, 3650));
    }

    @Override
    public PageResult<KlineVO> list(String symbol, KlineQuery query) {
        LocalDate start =
                query.getStartDate() == null || query.getStartDate().isBlank()
                        ? null
                        : LocalDate.parse(query.getStartDate());
        LocalDate end =
                query.getEndDate() == null || query.getEndDate().isBlank()
                        ? null
                        : LocalDate.parse(query.getEndDate());

        // 主窗口升序
        List<TechKlinePO> mainRows = loadAsc(symbol, start, end, query.getLimit());
        // warmup：往前多取 120 根用于递推指标
        List<TechKlinePO> warmupRows = List.of();
        if (!mainRows.isEmpty()) {
            LocalDate firstDate = mainRows.get(0).getDate();
            var warmupQuery =
                    new LambdaQueryWrapper<TechKlinePO>()
                            .eq(TechKlinePO::getSymbol, symbol)
                            .lt(TechKlinePO::getDate, firstDate)
                            .orderByDesc(TechKlinePO::getDate);
            List<TechKlinePO> warmupDesc = TopN.query(techKlineMapper, warmupQuery, IndicatorUtil.WARMUP);
            warmupRows = new ArrayList<>(warmupDesc);
            Collections.reverse(warmupRows);
        }
        List<TechKlinePO> allRows = new ArrayList<>(warmupRows);
        allRows.addAll(mainRows);

        int rowCount = allRows.size();
        double[] closePrices = new double[rowCount];
        double[] highPrices = new double[rowCount];
        double[] lowPrices = new double[rowCount];
        for (int i = 0; i < rowCount; i++) {
            closePrices[i] = IndicatorUtil.d(allRows.get(i).getClose());
            highPrices[i] = IndicatorUtil.d(allRows.get(i).getHigh());
            lowPrices[i] = IndicatorUtil.d(allRows.get(i).getLow());
        }
        List<java.util.Map<String, Double>> indicators =
                IndicatorUtil.calculate(closePrices, highPrices, lowPrices);
        String stockName = queryStockName(symbol);

        List<KlineVO> bars = new ArrayList<>();
        for (int i = warmupRows.size(); i < rowCount; i++)
            bars.add(MarketConverter.toKlineVO(allRows.get(i), stockName, indicators.get(i)));
        if (query.isOrderDesc()) Collections.reverse(bars);

        // K 线为区间返回（一次取回 limit 根），page 恒为 1，total 为本次返回条数
        return PageResult.of(bars.size(), bars, 1, Math.max(bars.size(), 1));
    }

    @Override
    public KlineStatsVO stats(String symbol) {
        long count =
                techKlineMapper.selectCount(
                        new LambdaQueryWrapper<TechKlinePO>().eq(TechKlinePO::getSymbol, symbol));
        String stockName = queryStockName(symbol);
        if (count == 0) return MarketConverter.toKlineStatsVO(symbol, stockName, 0, null, null);

        var latestWrapper =
                new LambdaQueryWrapper<TechKlinePO>()
                        .eq(TechKlinePO::getSymbol, symbol)
                        .orderByDesc(TechKlinePO::getDate);
        var earliestWrapper =
                new LambdaQueryWrapper<TechKlinePO>()
                        .eq(TechKlinePO::getSymbol, symbol)
                        .orderByAsc(TechKlinePO::getDate);
        var latestRows = TopN.latest(techKlineMapper, latestWrapper);
        var earliestRows = TopN.latest(techKlineMapper, earliestWrapper);
        TechKlinePO latest = latestRows.isEmpty() ? null : latestRows.get(0);
        TechKlinePO earliest = earliestRows.isEmpty() ? null : earliestRows.get(0);
        return MarketConverter.toKlineStatsVO(symbol, stockName, count, latest, earliest);
    }

    @Override
    public KlineVO one(String symbol, String tradeDate) {
        LocalDate date = LocalDate.parse(tradeDate);
        var rows =
                techKlineMapper.selectList(
                        new LambdaQueryWrapper<TechKlinePO>()
                                .eq(TechKlinePO::getSymbol, symbol)
                                .eq(TechKlinePO::getDate, date));
        if (rows.isEmpty()) throw new BusinessException(404, "K线不存在");

        // warmup 120 根算该日指标
        var warmupQuery =
                new LambdaQueryWrapper<TechKlinePO>()
                        .eq(TechKlinePO::getSymbol, symbol)
                        .lt(TechKlinePO::getDate, date)
                        .orderByDesc(TechKlinePO::getDate);
        List<TechKlinePO> warmupDesc = TopN.query(techKlineMapper, warmupQuery, IndicatorUtil.WARMUP);
        List<TechKlinePO> warmupRows = new ArrayList<>(warmupDesc);
        Collections.reverse(warmupRows);
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
        return MarketConverter.toKlineVO(
                rows.get(0), queryStockName(symbol), indicators.get(rowCount - 1));
    }

    @Override
    public KlineDeleteVO deleteAll(String symbol) {
        int deleted =
                techKlineMapper.delete(
                        new LambdaQueryWrapper<TechKlinePO>().eq(TechKlinePO::getSymbol, symbol));
        KlineDeleteVO result = new KlineDeleteVO();
        result.setSymbol(symbol);
        result.setDeletedCount(deleted);
        result.setMessage("成功删除股票 " + symbol + " 的全部 " + deleted + " 条K线");
        return result;
    }

    @Override
    public KlineDeleteVO deleteOne(String symbol, String tradeDate) {
        int deleted =
                techKlineMapper.delete(
                        new LambdaQueryWrapper<TechKlinePO>()
                                .eq(TechKlinePO::getSymbol, symbol)
                                .eq(TechKlinePO::getDate, LocalDate.parse(tradeDate)));
        KlineDeleteVO result = new KlineDeleteVO();
        result.setSymbol(symbol);
        result.setDeletedCount(deleted);
        result.setMessage("成功删除 " + deleted + " 条K线");
        return result;
    }
}
