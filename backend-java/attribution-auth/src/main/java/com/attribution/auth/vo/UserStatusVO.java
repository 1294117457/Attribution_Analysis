package com.attribution.auth.vo;

import lombok.Data;

/** 用户启用状态变更结果 */
@Data
public class UserStatusVO {
    private Integer id;
    private Boolean isActive;
}
