package com.attribution.market.converter;

import java.util.List;
import java.util.Map;

import com.attribution.market.entity.StockInfoPO;
import com.attribution.market.entity.TechKlinePO;
import com.attribution.market.util.IndicatorUtil;
import com.attribution.market.vo.AnalysisStockVO;
import com.attribution.market.vo.KlineStatsVO;
import com.attribution.market.vo.KlineVO;
import com.attribution.market.vo.StockInfoVO;
import com.attribution.market.vo.StockListItemVO;
import com.attribution.market.vo.StockMetaVO;
import com.attribution.market.vo.TechnicalSummaryVO;

/** 股票 / K 线 PO → VO 转换器 */
public final class MarketConverter {

    private MarketConverter() {
    }

    /** 上市日期统一格式化为 YYYYMMDD */
    public static String formatListDate(Object listDate) {
        if (listDate == null) return null;
        return String.valueOf(listDate).replace("-", "");
    }

    // ── 股票基础信息 ─────────────────────────────────────────

    public static StockInfoVO toStockInfoVO(StockInfoPO po) {
        if (po == null) return null;
        StockInfoVO vo = new StockInfoVO();
        vo.setSymbol(po.getSymbol());
        vo.setTsCode(po.getTsCode());
        vo.setName(po.getName());
        vo.setArea(po.getArea());
        vo.setIndustry(po.getIndustry());
        vo.setMarket(po.getMarket());
        vo.setExchange(po.getExchange());
        vo.setListDate(formatListDate(po.getListDate()));
        vo.setDelistDate(po.getDelistDate() == null ? null : String.valueOf(po.getDelistDate()));
        vo.setListStatus(po.getListStatus());
        vo.setIsHs(po.getIsHs());
        vo.setActName(po.getActName());
        vo.setActEntType(po.getActEntType());
        vo.setTotalShares(po.getTotalShares());
        return vo;
    }

    public static AnalysisStockVO toAnalysisStockVO(StockInfoPO po) {
        if (po == null) return null;
        AnalysisStockVO vo = new AnalysisStockVO();
        vo.setSymbol(po.getSymbol());
        vo.setName(po.getName());
        vo.setIndustry(po.getIndustry());
        vo.setMarket(po.getMarket());
        return vo;
    }

    public static StockListItemVO toStockListItemVO(StockInfoPO po) {
        if (po == null) return null;
        StockListItemVO vo = new StockListItemVO();
        vo.setSymbol(po.getSymbol());
        vo.setName(po.getName());
        vo.setIndustry(po.getIndustry());
        vo.setMarket(po.getMarket());
        vo.setExchange(po.getExchange());
        vo.setListStatus(po.getListStatus());
        return vo;
    }

    public static StockMetaVO toStockMetaVO(List<String> industries, List<String> markets, List<String> exchanges) {
        StockMetaVO vo = new StockMetaVO();
        vo.setIndustries(industries);
        vo.setMarkets(markets);
        vo.setExchanges(exchanges);
        return vo;
    }

    // ── K 线 ─────────────────────────────────────────────────

    /**
     * K 线 + 技术指标 → VO。
     *
     * @param po K 线 PO
     * @param stockName 股票名称（跨表查询得到）
     * @param indicators 该行对应的指标集合（可为 null，此时指标列全部置 null）
     */
    public static KlineVO toKlineVO(TechKlinePO po, String stockName, Map<String, Double> indicators) {
        if (po == null) return null;
        KlineVO vo = new KlineVO();
        vo.setSymbol(po.getSymbol());
        vo.setName(stockName == null ? po.getName() : stockName);
        vo.setDate(String.valueOf(po.getDate()));
        vo.setOpen(po.getOpen());
        vo.setHigh(po.getHigh());
        vo.setLow(po.getLow());
        vo.setClose(po.getClose());
        vo.setVolume(po.getVolume());
        vo.setAmount(po.getAmount());
        vo.setChangePct(po.getChangePct());
        applyIndicators(vo, indicators);
        return vo;
    }

    /** 填充 17 个技术指标列，指标缺失时置 null */
    private static void applyIndicators(KlineVO vo, Map<String, Double> indicators) {
        if (indicators == null) {
            for (String column : IndicatorUtil.COLS) {
                switch (column) {
                    case "ma5" -> vo.setMa5(null);
                    case "ma10" -> vo.setMa10(null);
                    case "ma20" -> vo.setMa20(null);
                    case "ma60" -> vo.setMa60(null);
                    case "ema12" -> vo.setEma12(null);
                    case "ema26" -> vo.setEma26(null);
                    case "macd_dif" -> vo.setMacdDif(null);
                    case "macd_dea" -> vo.setMacdDea(null);
                    case "macd_bar" -> vo.setMacdBar(null);
                    case "rsi6" -> vo.setRsi6(null);
                    case "rsi12" -> vo.setRsi12(null);
                    case "rsi24" -> vo.setRsi24(null);
                    case "kdj_k" -> vo.setKdjK(null);
                    case "kdj_d" -> vo.setKdjD(null);
                    case "kdj_j" -> vo.setKdjJ(null);
                    case "boll_up" -> vo.setBollUp(null);
                    case "boll_mid" -> vo.setBollMid(null);
                    case "boll_dn" -> vo.setBollDn(null);
                    default -> {
                        // 未知指标列忽略
                    }
                }
            }
            return;
        }
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

    public static KlineStatsVO toKlineStatsVO(
            String symbol, String name, long count, TechKlinePO latest, TechKlinePO earliest) {
        KlineStatsVO vo = new KlineStatsVO();
        vo.setSymbol(symbol);
        vo.setName(name);
        vo.setCount(count);
        if (latest != null) {
            vo.setLatestClose(IndicatorUtil.num(latest.getClose()));
            vo.setLatestVolume(latest.getVolume());
            vo.setEndDate(String.valueOf(latest.getDate()));
        }
        if (earliest != null) vo.setStartDate(String.valueOf(earliest.getDate()));
        return vo;
    }

    // ── 技术摘要 ─────────────────────────────────────────────

    /**
     * 技术形态摘要 Map → VO。
     *
     * <p>{@link IndicatorUtil#summarize} 内部以 Map 聚合计算，此处转换为强类型 VO 作为出参契约。
     */
    public static TechnicalSummaryVO toSummaryVO(Map<String, Object> summary) {
        if (summary == null) return null;
        TechnicalSummaryVO vo = new TechnicalSummaryVO();
        vo.setLatestClose(numOf(summary.get("latest_close")));
        vo.setPctChange1d(numOf(summary.get("pct_change_1d")));
        vo.setPctChange30d(numOf(summary.get("pct_change_30d")));
        vo.setMaAlignment(strOf(summary.get("ma_alignment")));
        vo.setMa5(numOf(summary.get("ma5")));
        vo.setMa10(numOf(summary.get("ma10")));
        vo.setMa20(numOf(summary.get("ma20")));
        vo.setMa60(numOf(summary.get("ma60")));
        vo.setMa5AboveMa20(boolOf(summary.get("ma5_above_ma20")));
        vo.setGoldenCrossRecent(boolOf(summary.get("golden_cross_recent")));
        vo.setMacdStatus(strOf(summary.get("macd_status")));
        vo.setMacdDif(numOf(summary.get("macd_dif")));
        vo.setMacdDea(numOf(summary.get("macd_dea")));
        vo.setMacdBar(numOf(summary.get("macd_bar")));
        vo.setRsi6(numOf(summary.get("rsi6")));
        vo.setRsiStatus(strOf(summary.get("rsi_status")));
        vo.setKdjK(numOf(summary.get("kdj_k")));
        vo.setKdjD(numOf(summary.get("kdj_d")));
        vo.setKdjJ(numOf(summary.get("kdj_j")));
        vo.setKdjStatus(strOf(summary.get("kdj_status")));
        vo.setBollUp(numOf(summary.get("boll_up")));
        vo.setBollMid(numOf(summary.get("boll_mid")));
        vo.setBollDn(numOf(summary.get("boll_dn")));
        vo.setBollPosition(strOf(summary.get("boll_position")));
        Object signals = summary.get("signals");
        vo.setSignals(signals instanceof List<?> list ? list.stream().map(String::valueOf).toList() : List.of());
        return vo;
    }

    private static Double numOf(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(value));
        } catch (Exception e) {
            return null;
        }
    }

    private static Boolean boolOf(Object value) {
        if (value == null) return null;
        if (value instanceof Boolean bool) return bool;
        return Boolean.parseBoolean(String.valueOf(value));
    }

    private static String strOf(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
