package com.attribution.market.dto;

import jakarta.validation.constraints.Size;

import lombok.Data;

/** 更新股票基础信息入参（PATCH 语义，全包装类型） */
@Data
public class StockUpdateRequest {
    @Size(max = 64, message = "股票名称最长 64 字符")
    private String name;

    @Size(max = 64, message = "行业最长 64 字符")
    private String industry;

    @Size(max = 32, message = "市场类型最长 32 字符")
    private String market;
}
