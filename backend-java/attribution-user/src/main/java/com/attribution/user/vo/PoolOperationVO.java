package com.attribution.user.vo;

import java.time.LocalDateTime;
import java.util.Map;

import lombok.Data;

/** 池操作记录视图对象 */
@Data
public class PoolOperationVO {
    private Integer id;
    private Integer poolId;
    private String operationType;
    private String status;
    private Map<String, Object> params;
    private Object resultSummary;
    private OperationProgressVO progress;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private LocalDateTime createdAt;
}
