package com.attribution.auth.dto;

import jakarta.validation.constraints.NotNull;

import lombok.Data;

/** 分配角色入参 */
@Data
public class AssignRoleRequest {
    @NotNull(message = "角色 ID 不能为空")
    private Integer roleId;
}
