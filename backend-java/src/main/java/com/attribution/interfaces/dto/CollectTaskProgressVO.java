package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 采集任务进度 - 实时进度查询
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CollectTaskProgressVO {

    private Long taskId;
    private String taskType;
    private String status;
    private Integer total;
    private Integer success;
    private Integer fail;
    private Integer skip;
    /** 0-100 */
    private Double progress;
    private String message;
    private String startedAt;
    private String finishedAt;
    private Integer durationMs;
    private Map<String, Object> params;
}
