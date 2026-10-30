package com.attribution.user.dto;

import jakarta.validation.constraints.Size;

import lombok.Data;

/**
 * 更新自选池入参（PATCH 语义）。
 *
 * <p>全部字段使用包装类型，用于区分「未传该字段」与「显式传 null」。
 */
@Data
public class PoolUpdateRequest {
    @Size(max = 64, message = "池名称最长 64 字符")
    private String name;

    @Size(max = 255, message = "描述最长 255 字符")
    private String description;

    @Size(max = 16, message = "颜色值最长 16 字符")
    private String color;

    @Size(max = 32, message = "图标最长 32 字符")
    private String icon;

    private Integer sortOrder;
}
