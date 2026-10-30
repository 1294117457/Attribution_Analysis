package com.attribution.market.entity;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

import com.baomidou.mybatisplus.annotation.*;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;

import lombok.Data;

/**
 * 采集任务日志（collector 写、Java 只读）：一行 = 一次采集任务。
 *
 * <p>表 {@code attribution.collect_logs}（复数），属业务库 → Mapper 不标 {@code @DS}。
 *
 * <p>⚠️ ★ 时间列必须用 {@link OffsetDateTime}（对应 PG 的 {@code timestamptz}），
 * <b>不能用 {@code LocalDateTime}</b>：
 * <ul>
 *   <li>DDL（{@code 03-rebuild-collect-logs.sql}）里这些列是 {@code TIMESTAMPTZ}；</li>
 *   <li>collector（Python）写入的是 <b>带时区</b> 的 aware datetime
 *       （{@code core/db.py} 明确要求 {@code timezone=True}，
 *       asyncpg 写 aware datetime 到 naive 列会直接报错）；</li>
 *   <li>用 {@code LocalDateTime} 读 {@code timestamptz} 列 → PG 驱动抛
 *       {@code "Cannot convert the column of type TIMESTAMPTZ to requested type
 *       java.time.LocalDateTime"} → 整个查询接口 500。</li>
 * </ul>
 * <p>（注意：{@code attribution} 库里其余表如 {@code sys_users} 的时间列仍是
 * naive {@code timestamp}，那些 PO 用 {@code LocalDateTime} 是对的 —— 别混改。）
 *
 * <p>规范见 {@code docs/开发文档/采集模块/采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md} §4.2。
 */
@Data
@TableName(value = "collect_logs", autoResultMap = true)
public class CollectLogPO {
    @TableId(type = IdType.INPUT)
    private String taskId;

    private String facet;
    private String name;
    private String kind;
    private String mode;

    private String triggerSource;
    private String triggerUser;

    @TableField(value = "params_json", typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> paramsJson;

    @TableField("range_start")
    private LocalDate rangeStart;

    @TableField("range_end")
    private LocalDate rangeEnd;

    private String status;
    private Integer progress;

    private Integer total;
    private Integer done;
    private Integer success;
    private Integer fail;
    private Integer skip;

    @TableField("saved_total")
    private Long savedTotal;

    private String message;
    private String error;

    @TableField(value = "detail", typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> detail;

    @TableField("created_at")
    private OffsetDateTime createdAt;

    @TableField("started_at")
    private OffsetDateTime startedAt;

    @TableField("finished_at")
    private OffsetDateTime finishedAt;

    @TableField("updated_at")
    private OffsetDateTime updatedAt;

    private Integer durationMs;

    private Boolean cancelRequested;

    @TableField("cancelled_at")
    private OffsetDateTime cancelledAt;

    @TableField("parent_task_id")
    private String parentTaskId;
}
