package com.attribution.user.vo;

import java.util.List;

import lombok.Data;

/** 批量添加成员结果 */
@Data
public class PoolAddMembersVO {
    private Integer poolId;
    private List<String> added;
    private List<String> skipped;
    private Integer totalAdded;
    private Integer totalSkipped;
}
