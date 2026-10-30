package com.attribution.user.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("pool_operations")
public class PoolOperationPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("pool_id")
    private Integer poolId;

    @TableField("operation_type")
    private String operationType;

    private String status;
    private String params;

    @TableField("result_summary")
    private String resultSummary;

    private String progress;

    @TableField("error_message")
    private String errorMessage;

    @TableField("started_at")
    private LocalDateTime startedAt;

    @TableField("finished_at")
    private LocalDateTime finishedAt;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
