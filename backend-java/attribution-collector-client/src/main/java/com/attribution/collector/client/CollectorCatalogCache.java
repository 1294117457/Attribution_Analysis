package com.attribution.collector.client;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;

/**
 * Collector 目录缓存（供 Java 侧做<b>动态</b> facet / strategy 校验）。
 *
 * <p>设计背景：
 * <ul>
 *   <li>旧实现把 facet 硬编码成 {@code Set.of("tech","capital","fundamental","news","sentiment")}
 *       —— Python 端新增一个 facet 的 service，Java 就会报「facet 非法」，
 *       直接卡死采集入口。</li>
 *   <li>策略校验同理：旧实现硬编码 {@code mode ∈ {condition, full}}，
 *       新契约是 {@code strategy ∈ {incremental, full}}。</li>
 * </ul>
 *
 * <p>本组件从 collector 的 {@code GET /api/collect/services} 拉目录并缓存，
 * <b>懒加载 + TTL</b>：首次访问时拉取，超过 TTL 后再访问时顺带刷新。
 * ⚠️ 本项目<b>不启用</b> {@code @EnableScheduling}（调度能力不在 Java 侧），
 * 所以不能用 {@code @Scheduled}，改为「访问触发 + TTL 判断」。
 *
 * <p>拉取失败时保留上一份缓存；从未成功加载过时降级为「不校验」，
 * 让请求透传到 collector，由 collector 给出权威错误。
 *
 * <p>⚠️ 本缓存只用于<b>快速拒绝明显非法</b>的请求，<b>不替代</b> collector 侧的权威判定
 * （collector 会校验 strategy 与 service 声明是否一致）。
 */
@Component
@RequiredArgsConstructor
public class CollectorCatalogCache {
    private static final Logger log = LoggerFactory.getLogger(CollectorCatalogCache.class);

    /** 目录缓存 TTL（毫秒）。 */
    private static final long TTL_MILLIS = 60_000L;

    /** 已知合法的采集方式（与 collect_logs.kind 的 CHECK 约束一致）。 */
    public static final Set<String> VALID_STRATEGIES = Set.of("incremental", "full");

    /** 旧前端兼容别名 → 新 strategy。 */
    private static final Map<String, String> LEGACY_STRATEGY_ALIAS =
            Map.of("condition", "incremental", "full", "full");

    private final CollectorClient client;

    /** key = service name，value = 目录项。 */
    private final Map<String, Map<String, Object>> byName = new ConcurrentHashMap<>();

    /** key = facet，value = 该 facet 下的 service name 集合。 */
    private final Map<String, Set<String>> byFacet = new ConcurrentHashMap<>();

    private volatile long loadedAtMillis = 0L;

    /** 拉取并刷新目录（失败时保留旧缓存）。 */
    public synchronized void refresh() {
        try {
            Map<String, Object> envelope = client.services();
            if (envelope == null) return;
            Object codeObj = envelope.get("code");
            if (codeObj instanceof Number num && num.intValue() >= 400) {
                log.warn("collector 目录不可用（code={}），保留旧缓存", codeObj);
                return;
            }
            Object dataObj = envelope.get("data");
            List<?> items = extractItems(dataObj, envelope);
            if (items == null) {
                log.warn("collector 目录结构异常，保留旧缓存");
                return;
            }
            Map<String, Map<String, Object>> newByName = new LinkedHashMap<>();
            Map<String, Set<String>> newByFacet = new LinkedHashMap<>();
            for (Object itemObj : items) {
                if (!(itemObj instanceof Map<?, ?> item)) continue;
                Object nameObj = item.get("name");
                Object facetObj = item.get("facet");
                if (nameObj == null) continue;
                String name = String.valueOf(nameObj);
                String facet = facetObj == null ? "" : String.valueOf(facetObj);
                Map<String, Object> normalized = new LinkedHashMap<>();
                item.forEach((k, v) -> normalized.put(String.valueOf(k), v));
                newByName.put(name, normalized);
                newByFacet.computeIfAbsent(facet, k -> ConcurrentHashMap.newKeySet()).add(name);
            }
            byName.clear();
            byName.putAll(newByName);
            byFacet.clear();
            byFacet.putAll(newByFacet);
            loadedAtMillis = System.currentTimeMillis();
            log.info("collector 目录已刷新：{} 个 service，{} 个 facet", newByName.size(), newByFacet.size());
        } catch (Exception e) {
            log.warn("刷新 collector 目录失败，保留旧缓存: {}", e.toString());
        }
    }

    /**
     * 取目录（必要时懒加载 / 刷新）。
     *
     * <p>首次调用或超过 TTL 时触发一次 {@link #refresh()}。
     * 刷新失败不影响本次调用——用旧缓存（或空缓存）继续。
     */
    private void ensureFresh() {
        if (!isLoaded() || isStale()) {
            refresh();
        }
    }

    /**
     * facet 是否合法。
     *
     * <p>⚠️ 目录尚未成功加载（collector 挂了）时返回 {@code true}
     * —— 降级为「不校验」，让请求透传到 collector，由 collector 给出权威错误。
     * 否则 collector 一挂，所有采集入口都会被 Java 层的「facet 非法」挡住，
     * 错误信息还完全指错方向。
     */
    public boolean isFacetKnown(String facet) {
        ensureFresh();
        if (!isLoaded()) return true;
        return byFacet.containsKey(facet);
    }

    /** 该 facet 下是否存在该 service。 */
    public boolean isServiceKnown(String facet, String name) {
        ensureFresh();
        if (!isLoaded()) return true;
        Set<String> names = byFacet.get(facet);
        return names != null && names.contains(name);
    }

    /** 目录项（未加载或不存在时返回 null）。 */
    public Map<String, Object> getService(String name) {
        ensureFresh();
        return byName.get(name);
    }

    /** service 声明的采集方式；未知时返回 null。 */
    public String getDeclaredStrategy(String name) {
        Map<String, Object> item = getService(name);
        if (item == null) return null;
        Object strategy = item.get("strategy");
        if (strategy == null) strategy = item.get("kind");
        return strategy == null ? null : String.valueOf(strategy);
    }

    /** 目录是否已成功加载过。 */
    public boolean isLoaded() {
        return loadedAtMillis > 0L && !byName.isEmpty();
    }

    /** 目录是否已过期（超过 TTL）。 */
    public boolean isStale() {
        if (!isLoaded()) return true;
        return (System.currentTimeMillis() - loadedAtMillis) > TTL_MILLIS;
    }

    /**
     * 归一化采集方式：优先 {@code strategy}，其次旧 {@code mode} 别名。
     *
     * @return 归一化后的 strategy；无值时返回 {@code null}
     */
    public static String normalizeStrategy(String raw) {
        if (raw == null) return null;
        String v = raw.trim();
        if (v.isEmpty()) return null;
        String mapped = LEGACY_STRATEGY_ALIAS.get(v);
        return mapped != null ? mapped : v;
    }

    private static List<?> extractItems(Object dataObj, Map<String, Object> envelope) {
        if (dataObj instanceof Map<?, ?> dataMap) {
            // collector 的 /services 返回 {total, list, page, page_size}
            for (String key : new String[] {"list", "items", "records"}) {
                Object list = dataMap.get(key);
                if (list instanceof List<?> l) return l;
            }
            return null;
        }
        if (dataObj instanceof List<?> l) return l;
        // 信封本身就是列表（兼容旧结构）
        Object items = envelope.get("items");
        if (items instanceof List<?> l) return l;
        return Collections.emptyList();
    }
}
