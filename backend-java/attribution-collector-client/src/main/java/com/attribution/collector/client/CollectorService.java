package com.attribution.collector.client;

import java.util.LinkedHashMap;
import java.util.Map;

import org.springframework.stereotype.Service;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;

/**
 * Collector 调用包装层。
 *
 * <p>规范见 {@code docs/规范文档/横切技术规范/基础设施规范.md}（外部调用）与
 * {@code docs/规范文档/纵向分层规范/Service层规范.md}（跨模块协作）。
 *
 * <p>⚠️ {@link ObjectMapper} 必须由 Spring 注入（复用全局 Jackson 配置：
 * {@code SNAKE_CASE} 命名策略等），**禁止** {@code new ObjectMapper()}——
 * 裸实例不带全局配置，序列化结果会与预期不一致。
 *
 * <p>采集方式契约（见 {@code docs/开发文档/采集模块/采集模块重构开发文档.md} §6.2）：
 * <ul>
 *   <li>{@code strategy}：{@code incremental}（增量）/ {@code full}（全量覆盖）</li>
 *   <li>{@code mode}：旧字段，兼容映射 {@code condition→incremental}、{@code full→full}</li>
 * </ul>
 */
@Service
@RequiredArgsConstructor
public class CollectorService {
    private final CollectorClient client;
    private final ObjectMapper objectMapper;

    public Map<String, Object> services() {
        return client.services();
    }

    public Object query(String serviceName, Map<String, Object> params) {
        try {
            Map<String, Object> queryResult =
                    client.query(serviceName, objectMapper.writeValueAsString(params == null ? Map.of() : params));
            return queryResult.get("data");
        } catch (Exception e) {
            throw new IllegalStateException("调用 collector 查询失败: " + serviceName, e);
        }
    }

    /**
     * 实时查询（透传整个信封，<b>不拆 data</b>）。
     *
     * <p>⚠️ 历史 bug：这里曾返回 {@code queryResult.get("data")}，
     * 而 fallback 在 collector 挂掉时返回 {@code {code:503, message:..., data:null}}，
     * 被拆包后变成 {@code null}，再被 Controller 包成 {@code {code:200, data:null}}
     * —— 前端误判为「查询成功但无数据」，彻底掩盖了 collector 宕机。
     *
     * <p>现在返回<b>整个信封</b>，让 {@code code=503} 原样透出。
     */
    public Map<String, Object> queryRaw(String serviceName, String paramsJson) {
        Map<String, Object> queryResult = client.query(serviceName, paramsJson == null ? "" : paramsJson);
        if (queryResult == null) {
            Map<String, Object> empty = new LinkedHashMap<>();
            empty.put("code", 503);
            empty.put("message", "collector unavailable");
            empty.put("data", null);
            return empty;
        }
        return queryResult;
    }

    /**
     * 创建后台采集任务。
     *
     * @param strategy       采集方式：{@code incremental} / {@code full}
     * @param params         采集参数（增量传 {@code start_date}/{@code end_date}，全量通常为空）
     * @param triggerSource  编排来源：{@code manual} / {@code retry}
     * @param parentTaskId   重跑时指向原任务（审计用）
     */
    public Map<String, Object> createTask(
            String facet, String serviceName, Map<String, Object> params, String strategy) {
        return createTask(facet, serviceName, params, strategy, null, null);
    }

    public Map<String, Object> createTask(
            String facet,
            String serviceName,
            Map<String, Object> params,
            String strategy,
            String triggerSource,
            String parentTaskId) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("strategy", strategy == null || strategy.isBlank() ? "incremental" : strategy);
        body.put("params", params == null ? Map.of() : params);
        if (triggerSource != null && !triggerSource.isBlank()) {
            body.put("trigger_source", triggerSource);
        }
        if (parentTaskId != null && !parentTaskId.isBlank()) {
            body.put("parent_task_id", parentTaskId);
        }
        return client.createTask(facet, serviceName, body);
    }

    public Map<String, Object> taskState(String taskId) {
        return client.taskState(taskId);
    }

    public Map<String, Object> taskList(Integer limit) {
        return client.taskList(limit == null ? 20 : limit);
    }

    /** 中断采集任务（只透传，中断逻辑在 collector 侧）。 */
    public Map<String, Object> cancelTask(String taskId) {
        return client.cancelTask(taskId);
    }
}
