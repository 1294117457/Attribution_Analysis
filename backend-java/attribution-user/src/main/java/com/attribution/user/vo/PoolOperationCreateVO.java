package com.attribution.user.vo;

import lombok.Data;

/** 创建池操作（采集任务）的返回结果 */
@Data
public class PoolOperationCreateVO {
    private Integer operationId;
    private Integer poolId;
    private String operationType;
    private String status;
    private Integer total;
    private String message;
}
