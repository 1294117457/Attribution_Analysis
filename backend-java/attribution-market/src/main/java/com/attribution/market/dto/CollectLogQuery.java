package com.attribution.market.dto;

import java.time.LocalDate;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;
import org.springframework.format.annotation.DateTimeFormat;

/**
 * 采集历史查询条件（查 PG collect_logs，collector 写、Java 只读）。
 *
 * <p>用 {@code @ModelAttribute} 绑定 + {@code @Valid} 校验，不手工装配。
 *
 * <p>⚠️ query string 绑定**不**受 Jackson {@code SNAKE_CASE} 影响，
 * 前端参数名必须与 Java 字段名完全一致（{@code pageSize} 而非 {@code page_size}）。
 */
@Data
public class CollectLogQuery {
    private String facet;
    private String name;
    private String status;
    private String triggerSource;

    /**
     * 按采集方式筛选：{@code incremental}（增量）/ {@code full}（全量覆盖）。
     *
     * <p>⚠️ {@code collect_logs.kind} 列现在承载<b>采集方式</b>（不再是旧的
     * {@code both}/{@code collect} 语义），因此这里的筛选值就是
     * {@code incremental}/{@code full}。
     */
    private String kind;

    /** 按创建时间范围筛选（起，含当天）。 */
    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
    private LocalDate startDate;

    /** 按创建时间范围筛选（止，含当天 23:59:59）。 */
    @DateTimeFormat(iso = DateTimeFormat.ISO.DATE)
    private LocalDate endDate;

    /** 只看有失败的任务。 */
    private Boolean hasFail;

    @Min(value = 1, message = "page 最小为 1")
    private Integer page = 1;

    @Min(value = 1, message = "pageSize 最小为 1")
    @Max(value = 100, message = "pageSize 最大为 100")
    private Integer pageSize = 20;

    public int getPage() {
        return page == null || page < 1 ? 1 : page;
    }

    public int getPageSize() {
        if (pageSize == null || pageSize < 1) return 20;
        return Math.min(pageSize, 100);
    }
}
