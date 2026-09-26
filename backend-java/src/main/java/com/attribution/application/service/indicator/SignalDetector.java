package com.attribution.application.service.indicator;

import com.attribution.domain.entity.TechKlineDailyEntity;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 技术形态检测器 - 根据 K 线历史计算技术指标摘要_ *
 * 输入：按日期升序排列_K 线列表（首元素为最旧日期）
 */
@Component
public class SignalDetector {

    /**
     * 对单_K 线快速检测关键信_     */
    public List<String> detect(TechKlineDailyEntity kline) {
        if (kline == null) {
            return Collections.emptyList();
        }
        List<String> signals = new ArrayList<>();

        // MA 多头
        if (kline.getMa5() != null && kline.getMa10() != null && kline.getMa20() != null
            && kline.getMa5() > kline.getMa10() && kline.getMa10() > kline.getMa20()) {
            signals.add("均线多头排列");
        }
        // MA 金叉
        if (kline.getMa5() != null && kline.getMa10() != null
            && kline.getMa5() > kline.getMa10()) {
            signals.add("MA5 > MA10");
        }
        // MACD
        if (kline.getMacdBar() != null && kline.getMacdBar() > 0) {
            signals.add("MACD 红柱");
        } else if (kline.getMacdBar() != null && kline.getMacdBar() < 0) {
            signals.add("MACD 绿柱");
        }
        // RSI
        if (kline.getRsi6() != null && kline.getRsi6() >= 80) {
            signals.add("RSI 严重超买");
        } else if (kline.getRsi6() != null && kline.getRsi6() >= 70) {
            signals.add("RSI 超买");
        } else if (kline.getRsi6() != null && kline.getRsi6() <= 20) {
            signals.add("RSI 严重超卖");
        } else if (kline.getRsi6() != null && kline.getRsi6() <= 30) {
            signals.add("RSI 超卖");
        }
        // BOLL
        if (kline.getBollUp() != null && kline.getClose() != null
            && kline.getClose() >= kline.getBollUp()) {
            signals.add("BOLL 突破上轨");
        } else if (kline.getBollDn() != null && kline.getClose() != null
            && kline.getClose() <= kline.getBollDn()) {
            signals.add("BOLL 跌破下轨");
        }

        return signals;
    }

    public TechnicalSummary summarize(List<TechKlineDailyEntity> klinesAsc) {
        if (klinesAsc == null || klinesAsc.isEmpty()) {
            return TechnicalSummary.builder().signals(List.of()).build();
        }

        TechKlineDailyEntity latest = klinesAsc.get(klinesAsc.size() - 1);
        Double latestClose = latest.getClose();

        Double pctChange1d = null;
        if (klinesAsc.size() >= 2) {
            TechKlineDailyEntity prev = klinesAsc.get(klinesAsc.size() - 2);
            if (prev.getClose() != null && prev.getClose() != 0) {
                pctChange1d = (latestClose - prev.getClose()) / prev.getClose() * 100.0;
            }
        }

        Double pctChange30d = null;
        if (klinesAsc.size() >= 31) {
            TechKlineDailyEntity past30 = klinesAsc.get(klinesAsc.size() - 31);
            if (past30.getClose() != null && past30.getClose() != 0) {
                pctChange30d = (latestClose - past30.getClose()) / past30.getClose() * 100.0;
            }
        }

        Double ma5 = latest.getMa5();
        Double ma10 = latest.getMa10();
        Double ma20 = latest.getMa20();
        Double ma60 = latest.getMa60();

        String maAlignment = null;
        Boolean ma5AboveMa20 = null;
        if (ma5 != null && ma10 != null && ma20 != null) {
            ma5AboveMa20 = ma5 > ma20;
            if (ma5 > ma10 && ma10 > ma20) {
                maAlignment = "多头排列";
            } else if (ma5 < ma10 && ma10 < ma20) {
                maAlignment = "空头排列";
            } else {
                maAlignment = "震荡";
            }
        }

        Boolean goldenCrossRecent = false;
        if (klinesAsc.size() >= 2) {
            TechKlineDailyEntity last = klinesAsc.get(klinesAsc.size() - 1);
            TechKlineDailyEntity prev = klinesAsc.get(klinesAsc.size() - 2);
            if (last.getMa5() != null && last.getMa10() != null
                && prev.getMa5() != null && prev.getMa10() != null) {
                if (prev.getMa5() <= prev.getMa10() && last.getMa5() > last.getMa10()) {
                    goldenCrossRecent = true;
                }
            }
        }

        Double macdDif = latest.getMacdDif();
        Double macdDea = latest.getMacdDea();
        Double macdBar = latest.getMacdBar();
        String macdStatus = null;
        if (macdBar != null) {
            if (macdBar > 0) {
                macdStatus = "多头";
            } else if (macdBar < 0) {
                macdStatus = "空头";
            } else {
                macdStatus = "中";
            }
        }

        Double rsi6 = latest.getRsi6();
        String rsiStatus = null;
        if (rsi6 != null) {
            if (rsi6 >= 80) rsiStatus = "严重超买";
            else if (rsi6 >= 70) rsiStatus = "超买";
            else if (rsi6 <= 20) rsiStatus = "严重超卖";
            else if (rsi6 <= 30) rsiStatus = "超卖";
            else rsiStatus = "中";
        }

        Double kdjK = latest.getKdjK();
        Double kdjD = latest.getKdjD();
        Double kdjJ = latest.getKdjJ();
        String kdjStatus = null;
        if (kdjK != null && kdjD != null) {
            if (kdjK > kdjD && kdjK > 80) kdjStatus = "超买";
            else if (kdjK < kdjD && kdjK < 20) kdjStatus = "超卖";
            else kdjStatus = "中";
        }

        Double bollUp = latest.getBollUp();
        Double bollMid = latest.getBollMid();
        Double bollDn = latest.getBollDn();
        String bollPosition = null;
        if (bollUp != null && bollDn != null && latestClose != null) {
            if (latestClose >= bollUp) bollPosition = "上轨突破";
            else if (latestClose <= bollDn) bollPosition = "下轨跌破";
            else if (bollMid != null && latestClose > bollMid) bollPosition = "中轨上方";
            else bollPosition = "中轨下方";
        }

        List<String> signals = new ArrayList<>();
        if (Boolean.TRUE.equals(ma5AboveMa20)) signals.add("MA5 上穿 MA20");
        if (Boolean.TRUE.equals(goldenCrossRecent)) signals.add("MA 金叉");
        if ("多头排列".equals(maAlignment)) signals.add("均线多头排列");
        if ("多头".equals(macdStatus) && macdBar != null && macdBar > 0) signals.add("MACD 红柱");
        if ("空头".equals(macdStatus)) signals.add("MACD 绿柱");
        if ("超买".equals(rsiStatus) || "严重超买".equals(rsiStatus)) signals.add("RSI 超买");
        if ("超卖".equals(rsiStatus) || "严重超卖".equals(rsiStatus)) signals.add("RSI 超卖");
        if ("上轨突破".equals(bollPosition)) signals.add("BOLL 突破上轨");

        return TechnicalSummary.builder()
            .latestClose(latestClose)
            .pctChange1d(pctChange1d)
            .pctChange30d(pctChange30d)
            .maAlignment(maAlignment)
            .ma5(ma5)
            .ma10(ma10)
            .ma20(ma20)
            .ma60(ma60)
            .ma5AboveMa20(ma5AboveMa20)
            .goldenCrossRecent(goldenCrossRecent)
            .macdStatus(macdStatus)
            .macdDif(macdDif)
            .macdDea(macdDea)
            .macdBar(macdBar)
            .rsi6(rsi6)
            .rsiStatus(rsiStatus)
            .kdjK(kdjK)
            .kdjD(kdjD)
            .kdjJ(kdjJ)
            .kdjStatus(kdjStatus)
            .bollUp(bollUp)
            .bollMid(bollMid)
            .bollDn(bollDn)
            .bollPosition(bollPosition)
            .signals(signals)
            .build();
    }
}
