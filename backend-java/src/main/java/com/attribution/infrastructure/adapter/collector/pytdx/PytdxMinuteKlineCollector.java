package com.attribution.infrastructure.adapter.collector.pytdx;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.cert.X509Certificate;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 分钟 K 线采集器（实时透传，不入库）。
 *
 * <p>采集路径：
 * <ol>
 *   <li><b>东方财富 push2his 接口（首选）</b>：
 *       <code>https://push2his.eastmoney.com/api/qt/stock/kline/get</code>
 *       支持 1/5/15/30/60 分钟周期，5min+ 可拿近 2 年历史，1min 近 5 个交易日。</li>
 *   <li><b>新浪 fallback（兜底）</b>：
 *       <code>https://image.sinajs.cn/newchart/v5/minute/{symbol}.js?scale={scale}</code>
 *       仅支持 1/5/15/30/60 分钟最近行情；不带复权数据。</li>
 * </ol>
 *
 * <p>对应旧 Python 工程 <code>infrastructure.collectors.pytdx.fetcher.PytdxFetcher</code>。
 * Java 工程没有 Python 通达信协议客户端，故采用公开 HTTP 接口代替。
 *
 * <p><b>HTTPS 实现说明</b>：JDK 11+ 内置 {@code java.net.http.HttpClient} 在部分网络环境
 * 对 push2his.eastmoney.com 握手不稳（"header parser received no bytes"）。
 * 这里改用 {@link HttpURLConnection}，对 HTTPS 公网行情接口兼容性最佳。
 */
@Slf4j
@Component
public class PytdxMinuteKlineCollector {

    @Value("${attribution.minute-kline.timeout-seconds:8}")
    private int timeoutSeconds;

    // 东财 kline 接口：返回字段用 f5x 索引
    // f51=date, f52=open, f53=close, f54=high, f55=low, f56=volume, f57=amount,
    // f58=amplitude, f59=pct_change, f60=change, f61=turnover
    private static final String EM_FIELDS = "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61";

    /**
     * 东财 end 参数默认填一个未来日期，使其返回所有历史分钟 K 线。
     * 东财 beg/end/lmt 三选二，end 用未来日期 + lmt=N 即可取最近 N 条。
     */
    private static final String EM_END_DEFAULT = "20500101";

    // 解析新浪 JS 中的 "min_data" JSON 字符串
    private static final Pattern SINA_MIN_DATA_PATTERN = Pattern.compile("min_data\\s*=\\s*\"([^\"]+)\"");

    // 共享的 SSLSocketFactory（信任所有证书，仅用于公网公开行情 API）
    private static final SSLSocketFactory TRUST_ALL_SSLF;
    static {
        try {
            TrustManager[] trustAll = new TrustManager[]{
                    new X509TrustManager() {
                        public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
                        public void checkClientTrusted(X509Certificate[] c, String a) { }
                        public void checkServerTrusted(X509Certificate[] c, String a) { }
                    }
            };
            SSLContext ctx = SSLContext.getInstance("TLS");
            ctx.init(null, trustAll, new java.security.SecureRandom());
            TRUST_ALL_SSLF = ctx.getSocketFactory();
        } catch (Exception e) {
            throw new RuntimeException("init SSLContext failed", e);
        }
    }

    /**
     * 拉取分钟 K 线（不落库，前端实时调用）。
     */
    public List<Map<String, Object>> fetchMinuteKlines(String symbol, String interval, int count) {
        if (symbol == null || symbol.length() != 6) {
            throw new IllegalArgumentException("symbol 必须为 6 位股票代码");
        }
        if (count <= 0 || count > 800) {
            count = Math.min(Math.max(count, 1), 800);
        }

        // 1. 首选：东财 kline 接口
        try {
            List<Map<String, Object>> eastMoney = fetchFromEastMoney(symbol, interval, count);
            if (!eastMoney.isEmpty()) {
                log.debug("东财 {} {}min 拉取到 {} 条", symbol, interval, eastMoney.size());
                return eastMoney;
            }
            log.warn("东财 {} {}min 返回空数组，尝试新浪 fallback", symbol, interval);
        } catch (Exception e) {
            log.warn("东财分钟 K 线拉取失败 {}: {}，尝试新浪 fallback", symbol, e.getMessage());
        }

        // 2. fallback：新浪
        try {
            List<Map<String, Object>> sina = fetchFromSina(symbol, interval, count);
            if (!sina.isEmpty()) {
                log.debug("新浪 fallback {} {}min 拉取到 {} 条", symbol, interval, sina.size());
            }
            return sina;
        } catch (Exception e) {
            log.warn("新浪分钟 K 线 fallback 失败 {}: {}", symbol, e.getMessage());
            return new ArrayList<>();
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  东方财富（首选）
    // ═══════════════════════════════════════════════════════════

    private List<Map<String, Object>> fetchFromEastMoney(String symbol, String interval, int count) throws Exception {
        String secid = symbolToEastMoneyMarket(symbol) + symbol;
        int klt = parseKlt(interval);

        String url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                + "?secid=" + secid
                + "&fields1=f1,f2,f3,f4,f5,f6"
                + "&fields2=" + EM_FIELDS
                + "&klt=" + klt
                + "&fqt=1"
                + "&end=" + EM_END_DEFAULT
                + "&lmt=" + count;

        String body = httpGet(url, "https://quote.eastmoney.com/");
        if (body == null || body.isEmpty()) {
            return new ArrayList<>();
        }
        return parseEastMoneyKlines(body, interval);
    }

    /**
     * 解析东财响应（单层 JSON，含 klines 数组）。
     *
     * <p>响应形如：
     * <pre>
     * {"rc":0,"data":{"klines":["2026-01-02 09:35,10.50,10.55,10.40,10.55,12345,234567.0,1.2,0.5,50,0.5,0.8", ...]}}
     * </pre>
     */
    private List<Map<String, Object>> parseEastMoneyKlines(String body, String interval) {
        // 用嵌套括号定位 "klines":[ ... ] 数组边界，避免 body.indexOf(']') 过早截断
        int idx = body.indexOf("\"klines\"");
        if (idx < 0) return new ArrayList<>();
        int arrStart = body.indexOf('[', idx);
        if (arrStart < 0) return new ArrayList<>();

        // 找到与 arrStart 配对的 ']'
        int arrEnd = -1;
        int depth = 0;
        boolean inQuote = false;
        boolean escape = false;
        for (int i = arrStart; i < body.length(); i++) {
            char c = body.charAt(i);
            if (escape) { escape = false; continue; }
            if (c == '\\') { escape = true; continue; }
            if (c == '"') { inQuote = !inQuote; continue; }
            if (inQuote) continue;
            if (c == '[') depth++;
            else if (c == ']') {
                depth--;
                if (depth == 0) { arrEnd = i; break; }
            }
        }
        if (arrEnd < 0) return new ArrayList<>();

        String arrContent = body.substring(arrStart + 1, arrEnd);
        if (arrContent.isEmpty()) return new ArrayList<>();

        List<Map<String, Object>> out = new ArrayList<>();
        for (String row : splitJsonArray(arrContent)) {
            // row 是 CSV 字符串："2026-01-02 09:35,10.50,10.55,10.40,10.55,12345,234567.0,1.2,0.5,50,0.5,0.8"
            // 注意日期里有空格，但 CSV 内不含逗号，可用 split(",") 安全切分
            String[] cols = row.split(",", -1);
            if (cols.length < 6) continue;
            try {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("datetime", cols[0].trim());
                item.put("interval", interval);
                item.put("open",  parseDouble(cols[1]));
                item.put("close", parseDouble(cols[2]));
                item.put("high",  parseDouble(cols[3]));
                item.put("low",   parseDouble(cols[4]));
                item.put("volume", parseLong(cols[5]));
                item.put("amount", cols.length > 6 ? parseDouble(cols[6]) : null);
                out.add(item);
            } catch (Exception ignore) {
                // 跳过单条异常
            }
        }
        return out;
    }

    /**
     * 简易 JSON 数组字符串切分（处理嵌套引号）。
     */
    private static List<String> splitJsonArray(String s) {
        List<String> out = new ArrayList<>();
        StringBuilder buf = new StringBuilder();
        boolean inQuote = false;
        boolean escape = false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (escape) { buf.append(c); escape = false; continue; }
            if (c == '\\') { buf.append(c); escape = true; continue; }
            if (c == '"') { inQuote = !inQuote; /* 不写入引号 */ continue; }
            if (c == ',' && !inQuote) {
                String token = buf.toString().trim();
                if (!token.isEmpty()) out.add(token);
                buf.setLength(0);
            } else {
                buf.append(c);
            }
        }
        if (buf.length() > 0) {
            String token = buf.toString().trim();
            if (!token.isEmpty()) out.add(token);
        }
        return out;
    }

    // ═══════════════════════════════════════════════════════════
    //  新浪（fallback）
    // ═══════════════════════════════════════════════════════════

    private List<Map<String, Object>> fetchFromSina(String symbol, String interval, int count) throws Exception {
        String scale = toSinaScale(interval);
        String sinaSymbol = symbolToSina(symbol);
        String url = "https://image.sinajs.cn/newchart/v5/minute/" + sinaSymbol + ".js?scale=" + scale;

        String body = httpGet(url, "https://finance.sina.com.cn/");
        if (body == null || body.isEmpty()) return new ArrayList<>();

        Matcher m = SINA_MIN_DATA_PATTERN.matcher(body);
        if (!m.find()) return new ArrayList<>();
        String minDataJson = m.group(1).replace("\\\\", "\\");

        List<Map<String, Object>> out = new ArrayList<>();
        for (String row : splitJsonArray(minDataJson)) {
            if (!row.startsWith("[")) continue;
            String inner = row.substring(1, row.length() - 1);
            String[] cols = splitTopLevel(inner);
            if (cols.length < 6) continue;
            try {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("datetime", stripQuotes(cols[0]));
                item.put("interval", interval);
                item.put("open",  parseDouble(cols[1]));
                item.put("close", parseDouble(cols[2]));
                item.put("high",  parseDouble(cols[3]));
                item.put("low",   parseDouble(cols[4]));
                item.put("volume", parseLong(cols[5]));
                item.put("amount", cols.length > 6 ? parseDouble(cols[6]) : null);
                out.add(item);
                if (out.size() >= count) break;
            } catch (Exception ignore) {
                // skip malformed
            }
        }
        return out;
    }

    /**
     * 切分顶层逗号分隔的字符串（不在 [ ] " " 内）。
     */
    private static String[] splitTopLevel(String s) {
        List<String> out = new ArrayList<>();
        StringBuilder buf = new StringBuilder();
        int depth = 0;
        boolean inQuote = false;
        boolean escape = false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (escape) { buf.append(c); escape = false; continue; }
            if (c == '\\') { buf.append(c); escape = true; continue; }
            if (c == '"') { inQuote = !inQuote; buf.append(c); continue; }
            if (!inQuote && (c == '[' || c == '{')) {
                depth++;
                buf.append(c);
            } else if (!inQuote && (c == ']' || c == '}')) {
                depth--;
                buf.append(c);
            } else if (c == ',' && depth == 0 && !inQuote) {
                out.add(buf.toString().trim());
                buf.setLength(0);
            } else {
                buf.append(c);
            }
        }
        if (buf.length() > 0) out.add(buf.toString().trim());
        return out.toArray(new String[0]);
    }

    private static String stripQuotes(String s) {
        s = s.trim();
        if (s.startsWith("\"") && s.endsWith("\"")) return s.substring(1, s.length() - 1);
        return s;
    }

    // ═══════════════════════════════════════════════════════════
    //  HTTP 通用方法（HttpURLConnection）
    // ═══════════════════════════════════════════════════════════

    /**
     * GET 请求并读取响应体（string）。
     *
     * <p>使用 {@link HttpURLConnection} 而非 JDK 11 HttpClient，
     * 兼容 push2his.eastmoney.com 的 HTTPS 握手。
     */
    private String httpGet(String urlStr, String referer) throws Exception {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        try {
            if (conn instanceof HttpsURLConnection https) {
                https.setSSLSocketFactory(TRUST_ALL_SSLF);
            }
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(timeoutSeconds * 1000);
            conn.setReadTimeout(timeoutSeconds * 1000);
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
            conn.setRequestProperty("Referer", referer);
            conn.setRequestProperty("Accept", "*/*");
            conn.setRequestProperty("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8");
            conn.setInstanceFollowRedirects(true);

            int code = conn.getResponseCode();
            if (code < 200 || code >= 300) {
                throw new IllegalStateException("HTTP " + code);
            }

            try (InputStream is = conn.getInputStream();
                 BufferedReader reader = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line);
                }
                return sb.toString();
            }
        } finally {
            conn.disconnect();
        }
    }

    // ═══════════════════════════════════════════════════════════
    //  工具
    // ═══════════════════════════════════════════════════════════

    private static String symbolToEastMoneyMarket(String symbol) {
        String prefix = symbol.substring(0, 2);
        if (prefix.equals("60") || prefix.equals("68") || prefix.equals("11") || prefix.equals("51")) {
            return "1."; // 上证
        }
        return "0."; // 深证
    }

    private static String symbolToSina(String symbol) {
        String prefix = symbol.substring(0, 2);
        if (prefix.equals("60") || prefix.equals("68") || prefix.equals("11") || prefix.equals("51")) {
            return "sh" + symbol;
        }
        return "sz" + symbol;
    }

    private static int parseKlt(String interval) {
        return switch (interval) {
            case "1min" -> 1;
            case "5min" -> 5;
            case "15min" -> 15;
            case "30min" -> 30;
            case "60min" -> 60;
            default -> 5;
        };
    }

    private static String toSinaScale(String interval) {
        return switch (interval) {
            case "1min" -> "1";
            case "5min" -> "5";
            case "15min" -> "15";
            case "30min" -> "30";
            case "60min" -> "60";
            default -> "5";
        };
    }

    private static Double parseDouble(String s) {
        if (s == null) return null;
        s = s.trim();
        if (s.isEmpty() || s.equalsIgnoreCase("null")) return null;
        try {
            return Double.parseDouble(s);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static Long parseLong(String s) {
        if (s == null) return null;
        s = s.trim();
        if (s.isEmpty() || s.equalsIgnoreCase("null")) return null;
        try {
            double d = Double.parseDouble(s);
            return (long) d;
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /**
     * 内部使用的简单查询：当日是否开盘（用于缓存失效判断，非核心）。
     */
    public boolean isTradeDayToday() {
        DayOfWeek dow = LocalDate.now().getDayOfWeek();
        return dow != DayOfWeek.SATURDAY && dow != DayOfWeek.SUNDAY;
    }
}
