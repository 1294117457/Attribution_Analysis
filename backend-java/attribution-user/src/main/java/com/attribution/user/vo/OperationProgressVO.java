package com.attribution.user.vo;

import java.util.List;

import lombok.Data;

/** 操作进度视图对象 */
@Data
public class OperationProgressVO {
    private Integer done = 0;
    private Integer total = 0;
    private Integer failed = 0;
}
