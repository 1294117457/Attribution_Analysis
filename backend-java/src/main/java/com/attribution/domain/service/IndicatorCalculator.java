package com.attribution.domain.service;

import com.attribution.domain.entity.TechKlineDailyEntity;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 技术指标计算器（domain service 层，纯计算，无 IO 依赖）
 *
 * <p>对应设计文档 docs/design/api/01-endpoint-spec.md §K 线指标计算
 *
 * <p>支持指标（与 tech_kline_dailys 表 17 个展宽列一一对应）：
 * <ul>
 *   <li>MA（5/10/20/60）：简单移动平均</li>
 *   <li>EMA（12/26）：指数移动平均</li>
 *   <li>MACD（DIF/DEA/BAR，参数 12/26/9）</li>
 *   <li>RSI（6/12/24）</li>
 *   <li>KDJ（K/D/J，参数 9/3/3）</li>
 *   <li>BOLL（上/中/下轨，参数 20/2）</li>
 * </ul>
 *
 * <p>移植自 Python {@code infrastructure.indicators.calculator.IndicatorCalculator}。
 */
@Slf4j
@Service
public class IndicatorCalculator {

    /**
     * 给 K 线列表补齐全部 17 个技术指标列。
     *
     * <p>调用约定：
     * <ul>
     *   <li>输入列表须按日期升序排列（MA/EMA 等指标依赖此前提）</li>
     *   <li>计算结果直接回填到每个 entity 的对应字段</li>
     *   <li>历史 K 线越多（MA60 需要至少 60 条），指标越准确</li>
     * </ul>
     *
     * @param entities 按日期升序排列的 K 线实体列表（会原地修改）
     */
    public void enrich(List<TechKlineDailyEntity> entities) {
        if (entities == null || entities.size() < 2) {
            return;
        }

        int n = entities.size();
        double[] close = new double[n];
        double[] high  = new double[n];
        double[] low   = new double[n];

        for (int i = 0; i < n; i++) {
            TechKlineDailyEntity e = entities.get(i);
            close[i] = e.getClose() != null ? e.getClose() : 0.0;
            high[i]  = e.getHigh()  != null ? e.getHigh()  : close[i];
            low[i]   = e.getLow()   != null ? e.getLow()   : close[i];
        }

        // ── MA ──────────────────────────────────────────────
        double[] ma5  = ma(close, 5);
        double[] ma10 = ma(close, 10);
        double[] ma20 = ma(close, 20);
        double[] ma60 = ma(close, 60);

        // ── EMA ─────────────────────────────────────────────
        double[] ema12 = ema(close, 12);
        double[] ema26 = ema(close, 26);

        // ── MACD（DIF / DEA / BAR） ────────────────────────
        double[] dif = new double[n];
        double[] dea = new double[n];
        double[] bar = new double[n];
        macd(close, dif, dea, bar);

        // ── RSI（6 / 12 / 24） ─────────────────────────────
        double[] rsi6  = rsi(close, 6);
        double[] rsi12 = rsi(close, 12);
        double[] rsi24 = rsi(close, 24);

        // ── KDJ（K / D / J） ───────────────────────────────
        double[] kdjK = new double[n];
        double[] kdjD = new double[n];
        double[] kdjJ = new double[n];
        kdj(high, low, close, kdjK, kdjD, kdjJ);

        // ── BOLL（UP / MID / DN） ───────────────────────────
        double[] bollUp  = new double[n];
        double[] bollMid = new double[n];
        double[] bollDn  = new double[n];
        boll(close, bollUp, bollMid, bollDn);

        // ── 回填 entity ─────────────────────────────────────
        for (int i = 0; i < n; i++) {
            TechKlineDailyEntity e = entities.get(i);
            e.setMa5(ma5[i]);
            e.setMa10(ma10[i]);
            e.setMa20(ma20[i]);
            e.setMa60(ma60[i]);
            e.setEma12(ema12[i]);
            e.setEma26(ema26[i]);
            e.setMacdDif(dif[i]);
            e.setMacdDea(dea[i]);
            e.setMacdBar(bar[i]);
            e.setRsi6(rsi6[i]);
            e.setRsi12(rsi12[i]);
            e.setRsi24(rsi24[i]);
            e.setKdjK(kdjK[i]);
            e.setKdjD(kdjD[i]);
            e.setKdjJ(kdjJ[i]);
            e.setBollUp(bollUp[i]);
            e.setBollMid(bollMid[i]);
            e.setBollDn(bollDn[i]);
        }

        log.debug("指标计算完成，共 {} 条", n);
    }

    // ═══════════════════════════════════════════════════════════
    //  MA — Simple Moving Average
    // ═══════════════════════════════════════════════════════════

    /**
     * 简单移动平均。
     *
     * @param prices 价格数组
     * @param window 窗口大小（≥ 1）
     * @return 与输入等长的数组，前 window-1 个为 Double.NaN
     */
    private static double[] ma(double[] prices, int window) {
        int n = prices.length;
        double[] out = new double[n];
        double sum = 0.0;
        for (int i = 0; i < n; i++) {
            sum += prices[i];
            if (i >= window) {
                sum -= prices[i - window];
                out[i] = sum / window;
            } else {
                out[i] = sum / (i + 1.0);
            }
        }
        return out;
    }

    // ═══════════════════════════════════════════════════════════
    //  EMA — Exponential Moving Average
    // ═══════════════════════════════════════════════════════════

    /**
     * 指数移动平均。
     *
     * @param prices 价格数组
     * @param span   跨距（≥ 1）
     * @return 与输入等长的数组
     */
    private static double[] ema(double[] prices, int span) {
        int n = prices.length;
        double[] out = new double[n];
        if (n == 0) return out;

        double alpha = 2.0 / (span + 1);
        out[0] = prices[0];
        for (int i = 1; i < n; i++) {
            out[i] = alpha * prices[i] + (1 - alpha) * out[i - 1];
        }
        return out;
    }

    // ═══════════════════════════════════════════════════════════
    //  MACD — DIF / DEA / BAR
    // ═══════════════════════════════════════════════════════════

    /**
     * MACD 计算（参数 12/26/9）。
     *
     * @param prices 价格数组
     * @param dif    输出 DIF 数组
     * @param dea   输出 DEA 数组
     * @param bar   输出 BAR（MACD 柱）数组
     */
    private static void macd(double[] prices, double[] dif, double[] dea, double[] bar) {
        int n = prices.length;
        double[] emaFast = ema(prices, 12);
        double[] emaSlow = ema(prices, 26);

        for (int i = 0; i < n; i++) {
            dif[i] = emaFast[i] - emaSlow[i];
        }

        // DEA = EMA(DIF, 9)
        double alpha = 2.0 / (9 + 1);
        dea[0] = dif[0];
        for (int i = 1; i < n; i++) {
            dea[i] = alpha * dif[i] + (1 - alpha) * dea[i - 1];
        }

        for (int i = 0; i < n; i++) {
            bar[i] = (dif[i] - dea[i]) * 2; // 柱 = (DIF - DEA) × 2
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  RSI — Relative Strength Index
    // ═══════════════════════════════════════════════════════════

    /**
     * RSI（相对强弱指数）。
     *
     * @param prices 价格数组
     * @param window 窗口（默认 14，akshare 用 6/12/24）
     * @return 与输入等长的数组，初期为 50（中性）
     */
    private static double[] rsi(double[] prices, int window) {
        int n = prices.length;
        double[] out = new double[n];
        if (n < 2) {
            if (n == 1) out[0] = 50.0;
            return out;
        }

        double avgGain = 0, avgLoss = 0;

        // 第一个变化量
        double delta = prices[1] - prices[0];
        if (delta > 0) avgGain = delta; else avgLoss = -delta;
        out[0] = 50.0;

        double alpha = 1.0 / window;
        for (int i = 1; i < n; i++) {
            if (i > 1) {
                delta = prices[i] - prices[i - 1];
                double gain = delta > 0 ? delta : 0;
                double loss = delta < 0 ? -delta : 0;
                avgGain = alpha * gain + (1 - alpha) * avgGain;
                avgLoss = alpha * loss + (1 - alpha) * avgLoss;
            }
            if (avgLoss == 0) {
                out[i] = 100.0;
            } else {
                double rs = avgGain / avgLoss;
                out[i] = 100.0 - 100.0 / (1.0 + rs);
            }
        }
        return out;
    }

    // ═══════════════════════════════════════════════════════════
    //  KDJ — Stochastic Oscillator
    // ═══════════════════════════════════════════════════════════

    /**
     * KDJ 计算（参数 9/3/3）。
     *
     * @param high  最高价数组
     * @param low   最低价数组
     * @param close 收盘价数组
     * @param kOut  输出 K 数组
     * @param dOut  输出 D 数组
     * @param jOut  输出 J 数组
     */
    private static void kdj(double[] high, double[] low, double[] close,
                             double[] kOut, double[] dOut, double[] jOut) {
        int n = close.length;
        int nPeriod = 9, m1 = 3, m2 = 3;

        double[] rsv = new double[n];
        for (int i = 0; i < n; i++) {
            int start = Math.max(0, i - nPeriod + 1);
            double lo = Double.MAX_VALUE, hi = Double.MIN_VALUE;
            for (int j = start; j <= i; j++) {
                if (low[j] < lo)  lo = low[j];
                if (high[j] > hi) hi = high[j];
            }
            double range = hi - lo;
            if (range < 1e-9) {
                rsv[i] = 50.0;
            } else {
                rsv[i] = (close[i] - lo) / range * 100.0;
            }
        }

        // K = EMA(RSV, m1)，D = EMA(K, m2)，J = 3K - 2D
        double alphaK = 2.0 / (m1 + 1);
        double alphaD = 2.0 / (m2 + 1);
        kOut[0] = rsv[0];
        dOut[0] = rsv[0];
        for (int i = 1; i < n; i++) {
            kOut[i] = alphaK * rsv[i] + (1 - alphaK) * kOut[i - 1];
            dOut[i] = alphaD * kOut[i] + (1 - alphaD) * dOut[i - 1];
        }
        for (int i = 0; i < n; i++) {
            jOut[i] = 3 * kOut[i] - 2 * dOut[i];
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  BOLL — Bollinger Bands
    // ═══════════════════════════════════════════════════════════

    /**
     * 布林带计算（参数 20/2）。
     *
     * @param prices   价格数组
     * @param upperOut 输出上轨数组
     * @param midOut   输出中轨数组
     * @param lowerOut 输出下轨数组
     */
    private static void boll(double[] prices, double[] upperOut, double[] midOut, double[] lowerOut) {
        int n = prices.length;
        int window = 20, nbStd = 2;

        for (int i = 0; i < n; i++) {
            int start = Math.max(0, i - window + 1);
            double sum = 0.0;
            for (int j = start; j <= i; j++) sum += prices[j];
            double mean = sum / (i - start + 1);

            double sqSum = 0.0;
            for (int j = start; j <= i; j++) {
                double d = prices[j] - mean;
                sqSum += d * d;
            }
            double std = Math.sqrt(sqSum / (i - start + 1));

            midOut[i]   = mean;
            upperOut[i] = mean + nbStd * std;
            lowerOut[i] = mean - nbStd * std;
        }
    }
}
