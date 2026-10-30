package com.attribution.auth.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Max;

import lombok.Data;

/** 用户列表查询条件（分页 + 关键字 + 启用状态筛选） */
@Data
public class UserQuery {
    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 200, message = "每页条数最多 200")
    private int pageSize = 20;

    /** 邮箱 / 昵称 模糊匹配 */
    private String keyword;

    /** null 表示不限 */
    private Boolean isActive;
}
