package com.attribution.user.dto;

import jakarta.validation.constraints.Size;

import lombok.Data;

/** 创建自选池入参 */
@Data
public class PoolCreateRequest {
    @Size(max = 64, message = "池名称最长 64 字符")
    private String name;

    @Size(max = 255, message = "描述最长 255 字符")
    private String description;

    /** watchlist / industry / strategy / custom */
    private String poolType = "custom";

    @Size(max = 16, message = "颜色值最长 16 字符")
    private String color;

    @Size(max = 32, message = "图标最长 32 字符")
    private String icon;
}
