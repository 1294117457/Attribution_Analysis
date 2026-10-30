package com.attribution.market.vo;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import lombok.Data;

/**
 * 采集历史行（collect_logs 原样透出，前端历史 tab 用）。
 *
 * <p>计数器口径：{@code total/done/success/fail/skip} 是<b>步数</b>，
 * {@code savedTotal} 是<b>行数</b>。
 */
@Data
public class CollectLogVO {
    private String taskId;
    private String facet;
    private String name;
    private String kind;
    private String mode;

    private String triggerSource;
    private String triggerUser;

    private Map<String, Object> paramsJson;
    private LocalDate rangeStart;
    private LocalDate rangeEnd;

    private String status;
    private Integer progress;

    private Integer total;
    private Integer done;
    private Integer success;
    private Integer fail;
    private Integer skip;

    private Long savedTotal;

    private String message;
    private String error;

    private List<Map<String, Object>> detail;

    /**
     * 时间字段用 {@code String}（ISO-8601 带时区），与前端
     * {@code CollectLogRow.createdAt: string | null} 的类型一致。
     *
     * <p>⚠️ 不能用 {@code LocalDateTime}：PG 列是 {@code timestamptz}，
     * 转成 {@code LocalDateTime} 会丢掉时区偏移，语义变成「本地时间」。
     */
    private String createdAt;
    private String startedAt;
    private String finishedAt;
    private String updatedAt;

    private Integer durationMs;

    private Boolean cancelRequested;
    private String cancelledAt;
    private String parentTaskId;
}
