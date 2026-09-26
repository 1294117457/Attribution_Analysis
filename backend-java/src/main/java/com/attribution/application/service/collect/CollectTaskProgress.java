package com.attribution.application.service.collect;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class CollectTaskProgress {

    private Long taskId;
    private String taskType;
    private String status;
    private Integer total;
    private Integer success;
    private Integer fail;
    private Integer skip;
    private Double progress;
    private String message;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private Integer durationMs;
}
