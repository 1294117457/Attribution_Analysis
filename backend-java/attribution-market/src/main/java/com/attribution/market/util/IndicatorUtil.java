package com.attribution.market.util;

import java.util.*;

/** 技术指标计算器（Java 版 IndicatorCalculator + SignalDetector，无第三方依赖） */
public final class IndicatorUtil {
    private IndicatorUtil() {}

    public static final List<String> COLS = List.of(
            "ma5",
            "ma10",
            "ma20",
            "ma60",
            "ema12",
            "ema26",
            "macd_dif",
            "macd_dea",
            "macd_bar",
            "rsi6",
            "rsi12",
            "rsi24",
            "kdj_k",
            "kdj_d",
            "kdj_j",
            "boll_up",
            "boll_mid",
            "boll_dn");
    public static final int WARMUP = 120;

    public static double d(Object o) {
        if (o == null) return Double.NaN;
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return Double.NaN;
        }
    }

    public static double[] ma(double[] s, int w) {
        double[] out = new double[s.length];
        Arrays.fill(out, Double.NaN);
        double sum = 0;
        for (int i = 0; i < s.length; i++) {
            sum += s[i];
            if (i >= w) sum -= s[i - w];
            if (i >= w - 1) out[i] = sum / w;
        }
        return out;
    }

    public static double[] ema(double[] s, int span) {
        double[] out = new double[s.length];
        Arrays.fill(out, Double.NaN);
        if (s.length == 0) return out;
        double a = 2.0 / (span + 1), e = s[0];
        for (int i = 0; i < s.length; i++) {
            e = i == 0 ? s[0] : a * s[i] + (1 - a) * e;
            out[i] = e;
        }
        for (int i = 0; i < Math.min(span - 1, s.length); i++) out[i] = Double.NaN;
        return out;
    }

    static double[] emaRaw(double[] s, double alpha) {
        double[] out = new double[s.length];
        int start = 0;
        while (start < s.length && Double.isNaN(s[start])) start++;
        if (start >= s.length) {
            Arrays.fill(out, Double.NaN);
            return out;
        }
        double e = s[start];
        for (int i = 0; i < s.length; i++) {
            if (i < start) {
                out[i] = Double.NaN;
                continue;
            }
            if (Double.isNaN(s[i])) {
                out[i] = Double.NaN;
                continue;
            }
            e = i == start ? s[i] : alpha * s[i] + (1 - alpha) * e;
            out[i] = e;
        }
        return out;
    }

    public static double[][] macd(double[] close) {
        double[] ef = emaRaw(close, 2.0 / 13), es = emaRaw(close, 2.0 / 27);
        double[] dif = new double[close.length];
        for (int i = 0; i < close.length; i++)
            dif[i] = (Double.isNaN(ef[i]) || Double.isNaN(es[i])) ? Double.NaN : ef[i] - es[i];
        double[] dea = emaRaw(dif, 2.0 / 10);
        double[] bar = new double[close.length];
        for (int i = 0; i < close.length; i++)
            bar[i] = (Double.isNaN(dif[i]) || Double.isNaN(dea[i])) ? Double.NaN : (dif[i] - dea[i]) * 2;
        for (int i = 0; i < Math.min(25, close.length); i++) dif[i] = Double.NaN;
        for (int i = 0; i < Math.min(33, close.length); i++) {
            dea[i] = Double.NaN;
            bar[i] = Double.NaN;
        }
        return new double[][] {dif, dea, bar};
    }

    public static double[] rsi(double[] close, int w) {
        double[] out = new double[close.length];
        Arrays.fill(out, Double.NaN);
        if (close.length == 0) return out;
        double a = 1.0 / w, ag = 0, al = 0;
        boolean init = false;
        for (int i = 0; i < close.length; i++) {
            double delta = i == 0 ? 0 : close[i] - close[i - 1];
            double g = Math.max(delta, 0), l = Math.max(-delta, 0);
            if (i == 0) {
                ag = g;
                al = l;
            } else {
                ag = a * g + (1 - a) * ag;
                al = a * l + (1 - a) * al;
            }
            if (i >= w) {
                double t = ag + al;
                out[i] = t == 0 ? 50.0 : 100 * ag / t;
            }
        }
        return out;
    }

    public static double[][] kdj(double[] high, double[] low, double[] close) {
        int n = high.length;
        double[] k = new double[n], d = new double[n], j = new double[n];
        Arrays.fill(k, Double.NaN);
        Arrays.fill(d, Double.NaN);
        Arrays.fill(j, Double.NaN);
        double[] rsv = new double[n];
        Arrays.fill(rsv, Double.NaN);
        for (int i = 8; i < n; i++) {
            double ln = Double.MAX_VALUE, hx = -Double.MAX_VALUE;
            for (int t = i - 8; t <= i; t++) {
                ln = Math.min(ln, low[t]);
                hx = Math.max(hx, high[t]);
            }
            rsv[i] = (close[i] - ln) / (hx - ln + 1e-9) * 100;
        }
        double[] kk = emaRaw(rsv, 1.0 / 3), dd = emaRaw(kk, 1.0 / 3);
        for (int i = 0; i < n; i++) {
            k[i] = kk[i];
            d[i] = dd[i];
            if (!Double.isNaN(k[i]) && !Double.isNaN(d[i])) j[i] = 3 * k[i] - 2 * d[i];
        }
        return new double[][] {k, d, j};
    }

    public static double[][] boll(double[] close) {
        int n = close.length;
        double[] up = new double[n], mid = new double[n], dn = new double[n];
        Arrays.fill(up, Double.NaN);
        Arrays.fill(mid, Double.NaN);
        Arrays.fill(dn, Double.NaN);
        for (int i = 19; i < n; i++) {
            double s = 0;
            for (int t = i - 19; t <= i; t++) s += close[t];
            double m = s / 20, v = 0;
            for (int t = i - 19; t <= i; t++) v += (close[t] - m) * (close[t] - m);
            double sd = Math.sqrt(v / 19);
            mid[i] = m;
            up[i] = m + 2 * sd;
            dn[i] = m - 2 * sd;
        }
        return new double[][] {up, mid, dn};
    }

    /** 输入升序 close/high/low，返回每行 18 列（NaN 表示不足） */
    public static List<Map<String, Double>> calculate(double[] close, double[] high, double[] low) {
        int n = close.length;
        double[] ma5 = ma(close, 5), ma10 = ma(close, 10), ma20 = ma(close, 20), ma60 = ma(close, 60);
        double[] e12 = ema(close, 12), e26 = ema(close, 26);
        double[][] m = macd(close);
        double[] r6 = rsi(close, 6), r12 = rsi(close, 12), r24 = rsi(close, 24);
        double[][] kj = kdj(high, low, close);
        double[][] b = boll(close);
        List<Map<String, Double>> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            Map<String, Double> r = new LinkedHashMap<>();
            double[] v = {
                ma5[i], ma10[i], ma20[i], ma60[i], e12[i], e26[i], m[0][i], m[1][i], m[2][i], r6[i], r12[i], r24[i],
                kj[0][i], kj[1][i], kj[2][i], b[0][i], b[1][i], b[2][i]
            };
            for (int k = 0; k < COLS.size(); k++) r.put(COLS.get(k), Double.isNaN(v[k]) ? null : v[k]);
            out.add(r);
        }
        return out;
    }

    static Double g(Map<String, Double> m, String k) {
        return m.get(k);
    }

    /** 技术形态摘要（Java 版 SignalDetector.summarize），输入升序 K 线 close/change + 指标 */
    public static Map<String, Object> summarize(double[] closes, Double[] changePct, List<Map<String, Double>> inds) {
        int n = closes.length;
        Map<String, Double> L = inds.get(n - 1);
        Map<String, Double> P = n > 1 ? inds.get(n - 2) : null;
        Map<String, Double> P5 = n >= 6 ? inds.get(n - 6) : null;
        List<String> signals = new ArrayList<>();
        String maAlign = "neutral";
        if (L.get("ma5") != null && L.get("ma10") != null && L.get("ma20") != null) {
            if (L.get("ma5") > L.get("ma10") && L.get("ma10") > L.get("ma20")) {
                maAlign = "bullish";
                signals.add("MA 多头排列");
            } else if (L.get("ma5") < L.get("ma10") && L.get("ma10") < L.get("ma20")) {
                maAlign = "bearish";
                signals.add("MA 空头排列");
            }
        }
        boolean above = L.get("ma5") != null && L.get("ma20") != null && L.get("ma5") > L.get("ma20");
        boolean cross = false;
        if (P != null
                && P5 != null
                && P5.get("ma5") != null
                && P5.get("ma20") != null
                && P.get("ma5") != null
                && P.get("ma20") != null
                && P5.get("ma5") <= P5.get("ma20")
                && P.get("ma5") > P.get("ma20")) {
            cross = true;
            signals.add("MA 金叉");
        }
        String macdSt = "neutral";
        if (L.get("macd_dif") != null && L.get("macd_dea") != null) {
            if (P != null && P.get("macd_dif") != null && P.get("macd_dea") != null) {
                if (P.get("macd_dif") <= P.get("macd_dea") && L.get("macd_dif") > L.get("macd_dea")) {
                    macdSt = "golden_cross";
                    signals.add("MACD 金叉");
                } else if (P.get("macd_dif") >= P.get("macd_dea") && L.get("macd_dif") < L.get("macd_dea")) {
                    macdSt = "death_cross";
                    signals.add("MACD 死叉");
                }
            }
            if (macdSt.equals("neutral"))
                macdSt = L.get("macd_dif") > 0 ? "above_zero" : (L.get("macd_dif") < 0 ? "below_zero" : "neutral");
        }
        String rsiSt = "neutral";
        double rsi6 = L.get("rsi6") == null ? 50.0 : L.get("rsi6");
        if (L.get("rsi6") != null) {
            if (L.get("rsi6") > 70) {
                rsiSt = "overbought";
                signals.add("RSI 超买");
            } else if (L.get("rsi6") < 30) {
                rsiSt = "oversold";
                signals.add("RSI 超卖");
            }
        }
        String kdjSt = "neutral";
        if (L.get("kdj_k") != null && L.get("kdj_d") != null) {
            if (P != null && P.get("kdj_k") != null && P.get("kdj_d") != null) {
                if (P.get("kdj_k") <= P.get("kdj_d") && L.get("kdj_k") > L.get("kdj_d")) {
                    kdjSt = "golden_cross";
                    signals.add("KDJ 金叉");
                } else if (P.get("kdj_k") >= P.get("kdj_d") && L.get("kdj_k") < L.get("kdj_d")) {
                    kdjSt = "death_cross";
                    signals.add("KDJ 死叉");
                }
            }
            if (kdjSt.equals("neutral") && L.get("kdj_j") != null) {
                if (L.get("kdj_j") > 100) {
                    kdjSt = "overbought";
                    signals.add("KDJ 超买");
                } else if (L.get("kdj_j") < 0) {
                    kdjSt = "oversold";
                    signals.add("KDJ 超卖");
                }
            }
        }
        String bollPos = "middle";
        double lc = closes[n - 1];
        if (L.get("boll_up") != null && L.get("boll_dn") != null && L.get("boll_mid") != null) {
            if (lc > L.get("boll_up")) {
                bollPos = "above_upper";
                signals.add("突破布林上轨");
            } else if (lc < L.get("boll_dn")) {
                bollPos = "below_lower";
                signals.add("跌破布林下轨");
            } else if (lc > L.get("boll_mid")) bollPos = "upper_half";
            else bollPos = "lower_half";
        }
        double p1d = changePct[n - 1] == null ? 0.0 : changePct[n - 1];
        double p30d = 0;
        if (n >= 30 && closes[n - 30] > 0) p30d = (lc / closes[n - 30] - 1) * 100;
        Map<String, Object> o = new LinkedHashMap<>();
        o.put("latest_close", lc);
        o.put("pct_change_1d", p1d);
        o.put("pct_change_30d", p30d);
        o.put("ma_alignment", maAlign);
        o.put("ma5", L.get("ma5"));
        o.put("ma10", L.get("ma10"));
        o.put("ma20", L.get("ma20"));
        o.put("ma60", L.get("ma60"));
        o.put("ma5_above_ma20", above);
        o.put("golden_cross_recent", cross);
        o.put("macd_status", macdSt);
        o.put("macd_dif", nn(L.get("macd_dif")));
        o.put("macd_dea", nn(L.get("macd_dea")));
        o.put("macd_bar", nn(L.get("macd_bar")));
        o.put("rsi6", rsi6);
        o.put("rsi_status", rsiSt);
        o.put("kdj_k", nn(L.get("kdj_k")));
        o.put("kdj_d", nn(L.get("kdj_d")));
        o.put("kdj_j", nn(L.get("kdj_j")));
        o.put("kdj_status", kdjSt);
        o.put("boll_up", L.get("boll_up"));
        o.put("boll_mid", L.get("boll_mid"));
        o.put("boll_dn", L.get("boll_dn"));
        o.put("boll_position", bollPos);
        o.put("signals", signals);
        return o;
    }

    static double nn(Double v) {
        return v == null ? 0.0 : v;
    }

    public static Double num(Object o) {
        if (o == null) return null;
        if (o instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(o));
        } catch (Exception e) {
            return null;
        }
    }

    public static String iso(Object o) {
        return o == null ? null : String.valueOf(o);
    }

    public static String color(Double pct) {
        if (pct == null) return "flat";
        return pct > 0 ? "up" : (pct < 0 ? "down" : "flat");
    }
}
