package com.attribution.auth.dto;

import jakarta.validation.constraints.NotNull;

import lombok.Data;

/** 启用/禁用用户入参（PATCH 语义，单字段布尔） */
@Data
public class UpdateStatusRequest {
    @NotNull(message = "启用状态不能为空")
    private Boolean isActive;
}
