package com.attribution.concept.vo;

import lombok.Data;

/** 池归属关系视图对象 */
@Data
public class PoolMembershipVO {
    private Integer poolId;
    private String name;
    private String poolType;
    private String joinedAt;
}
