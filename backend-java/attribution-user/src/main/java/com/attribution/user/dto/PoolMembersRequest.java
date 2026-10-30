package com.attribution.user.dto;

import java.util.List;

import jakarta.validation.constraints.NotEmpty;

import lombok.Data;

/** 批量添加 / 移除池成员入参 */
@Data
public class PoolMembersRequest {
    @NotEmpty(message = "股票代码列表不能为空")
    private List<String> symbols;

    /** 是否校验股票存在（默认 true） */
    private Boolean validateExists = true;
}
