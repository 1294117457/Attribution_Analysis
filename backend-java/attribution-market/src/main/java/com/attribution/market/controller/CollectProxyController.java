package com.attribution.market.controller;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.attribution.collector.client.CollectorCatalogCache;
import com.attribution.collector.client.CollectorService;
import com.attribution.common.exception.BusinessException;

import lombok.RequiredArgsConstructor;

/**
 * 采集管理代理：前端 /api/collect/** 经 Java 透传到 collector-python（内网 :8001）。
 * 采集一律走后台任务（建任务→轮询进度），同步 collect 入口已下线；实时查询走 query 透传。
 *
 * <p>采集方式契约（见 {@code docs/开发文档/采集模块/采集模块重构开发文档.md}）：
 * <ul>
 *   <li>{@code strategy=incremental} —— 增量，前端只暴露时间范围</li>
 *   <li>{@code strategy=full} —— 全量覆盖，前端只暴露一个按钮</li>
 *   <li>{@code strategy=realtime} —— 实时直查，不支持建任务（由 collector 拒绝）</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/collect")
@RequiredArgsConstructor
public class CollectProxyController {
    private final CollectorService collectorService;
    private final CollectorCatalogCache catalogCache;

    @GetMapping("/services")
    public ResponseEntity<Map<String, Object>> services() {
        Map<String, Object> servicesResult = collectorService.services();
        return ResponseEntity.ok(servicesResult);
    }

    /**
     * 实时查询（透传）。
     *
     * <p>⚠️ <b>不拆信封</b>：collector 的 {@code code/message} 原样透出。
     * 否则 collector 宕机时 fallback 的 {@code {code:503, data:null}} 会被包成
     * {@code {code:200, data:null}}，前端误判为「查询成功但无数据」，
     * 把 collector 宕机彻底掩盖掉。
     *
     * <p>前端 {@code unwrap()} 按 {@code code>=400} 判错，行为与其它端点一致。
     */
    @GetMapping("/query/{name}")
    public ResponseEntity<Map<String, Object>> query(
            @PathVariable String name,
            @RequestParam(value = "params", required = false, defaultValue = "") String paramsJson) {
        return ResponseEntity.ok(collectorService.queryRaw(name, paramsJson));
    }

    /**
     * 创建后台采集任务：校验后透传，立即返回 task_id（进度查 /tasks/{taskId}）。
     *
     * <p>请求体：
     * <pre>
     * { "strategy": "incremental", "params": { "start_date": "...", "end_date": "..." },
     *   "trigger_source": "manual", "parent_task_id": null }
     * </pre>
     */
    @PostMapping("/tasks/{facet}/{name}")
    public ResponseEntity<Map<String, Object>> createTask(
            @PathVariable String facet,
            @PathVariable String name,
            @RequestBody(required = false) Map<String, Object> body) {
        String rawStrategy = body == null ? null : stringOf(body.get("strategy"));
        // ⚠️ 旧前端兼容：仍可能传 mode=condition/full
        if (rawStrategy == null || rawStrategy.isBlank()) {
            rawStrategy = stringOf(body == null ? null : body.get("mode"));
        }
        String strategy = CollectorCatalogCache.normalizeStrategy(rawStrategy);
        Object rawParams = body == null ? null : body.get("params");
        @SuppressWarnings("unchecked")
        Map<String, Object> params = rawParams instanceof Map ? (Map<String, Object>) rawParams : Map.of();
        String triggerSource = body == null ? null : stringOf(body.get("trigger_source"));
        String parentTaskId = body == null ? null : stringOf(body.get("parent_task_id"));

        TaskValidator.validate(facet, name, strategy, params, catalogCache);
        Map<String, Object> taskResult =
                collectorService.createTask(facet, name, params, strategy, triggerSource, parentTaskId);
        return ResponseEntity.ok(taskResult);
    }

    @GetMapping("/tasks/{taskId}")
    public ResponseEntity<Map<String, Object>> taskState(@PathVariable String taskId) {
        if (taskId == null || !taskId.matches("[0-9a-fA-F]{8,64}")) throw new BusinessException(400, "taskId 非法");
        return ResponseEntity.ok(collectorService.taskState(taskId));
    }

    @GetMapping("/tasks")
    public ResponseEntity<Map<String, Object>> taskList(
            @RequestParam(value = "limit", required = false, defaultValue = "20") Integer limit) {
        if (limit == null || limit < 1 || limit > 100) throw new BusinessException(400, "limit 取值范围 1~100");
        return ResponseEntity.ok(collectorService.taskList(limit));
    }

    /** 中断采集任务：只透传，中断逻辑在 collector 侧 */
    @PostMapping("/tasks/{taskId}/cancel")
    public ResponseEntity<Map<String, Object>> cancelTask(@PathVariable String taskId) {
        if (taskId == null || !taskId.matches("[0-9a-fA-F]{8,64}")) throw new BusinessException(400, "taskId 非法");
        return ResponseEntity.ok(collectorService.cancelTask(taskId));
    }

    private static String stringOf(Object v) {
        return v == null ? null : String.valueOf(v);
    }

    /**
     * 创建任务前的轻校验：fail fast，<b>不替代</b> collector 侧的最终校验。
     *
     * <p>校验分两层：
     * <ol>
     *   <li><b>纯语法校验</b>（永远生效）：name 格式、strategy 值域、日期格式与区间方向</li>
     *   <li><b>目录校验</b>（目录可用时生效）：facet / service 是否存在于 collector 目录</li>
     * </ol>
     * 目录校验依赖 collector 可用性；collector 挂掉时降级为「不校验」，
     * 让请求透传过去由 collector 给出权威错误，而不是在 Java 层报「facet 非法」。
     */
    static final class TaskValidator {
        private static final DateTimeFormatter DAY = DateTimeFormatter.ISO_LOCAL_DATE;
        /** 单次任务允许的最大区间跨度（与 collector 的 MAX_RANGE_DAYS 对齐）。 */
        private static final int MAX_RANGE_DAYS = 366;

        static void validate(
                String facet,
                String name,
                String strategy,
                Map<String, Object> params,
                CollectorCatalogCache catalog) {
            // ── ① 语法校验（永远生效）────────────────────────
            if (facet == null || facet.isBlank()) throw new BusinessException(400, "facet 不能为空");
            if (name == null || !name.matches("[a-z0-9_]{1,64}")) throw new BusinessException(400, "name 非法");
            if (strategy == null || strategy.isBlank())
                throw new BusinessException(400, "strategy 不能为空");
            if (!CollectorCatalogCache.VALID_STRATEGIES.contains(strategy))
                throw new BusinessException(400, "strategy 仅支持 incremental/full");

            if (params != null && params.size() > 64) throw new BusinessException(400, "params 参数过多");

            LocalDate s = null, e = null, t = null;
            if (params != null) {
                s = parseDay(params.get("start_date"), "start_date");
                e = parseDay(params.get("end_date"), "end_date");
                t = parseDay(params.get("trade_date"), "trade_date");
            }
            if (t != null && (s != null || e != null))
                throw new BusinessException(400, "trade_date 不能与 start_date/end_date 同传");
            if (s != null && e != null) {
                if (s.isAfter(e)) throw new BusinessException(400, "start_date 不能晚于 end_date");
                long days = java.time.temporal.ChronoUnit.DAYS.between(s, e);
                if (days > MAX_RANGE_DAYS)
                    throw new BusinessException(400, "日期范围最多 " + MAX_RANGE_DAYS + " 天");
            }
            // ★ 全量覆盖不接受日期参数（覆盖域由 service 自行界定）
            if ("full".equals(strategy) && (s != null || e != null || t != null))
                throw new BusinessException(400, "全量覆盖采集不接受日期参数");

            // ── ② 目录校验（目录可用时生效）────────────────────
            if (catalog == null || !catalog.isLoaded()) return;
            if (!catalog.isFacetKnown(facet))
                throw new BusinessException(400, "facet 非法: " + facet);
            if (!catalog.isServiceKnown(facet, name))
                throw new BusinessException(400, "collector 不存在: " + facet + "/" + name);
            String declared = catalog.getDeclaredStrategy(name);
            if (declared != null && !declared.isBlank() && !declared.equals(strategy)) {
                // service 声明 realtime → 不可建任务
                if ("realtime".equals(declared))
                    throw new BusinessException(400, name + " 是实时查询服务，不支持后台任务");
                throw new BusinessException(400,
                        name + " 声明的采集方式是 " + declared + "，不接受 " + strategy);
            }
        }

        private static LocalDate parseDay(Object value, String key) {
            if (value == null) return null;
            String str = String.valueOf(value).trim();
            if (str.isEmpty()) return null;
            try {
                return LocalDate.parse(str, DAY);
            } catch (DateTimeParseException ex) {
                throw new BusinessException(400, key + " 非法，期望 YYYY-MM-DD");
            }
        }
    }
}
