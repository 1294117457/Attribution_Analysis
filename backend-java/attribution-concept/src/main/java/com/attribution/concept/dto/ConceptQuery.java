package com.attribution.concept.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** 概念列表查询条件 */
@Data
public class ConceptQuery {
    /** 名称模糊匹配 / 指数编码精确匹配 */
    private String keyword;

    /** null 表示不限 */
    private Boolean isActive;

    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 100, message = "每页条数最多 100")
    private int pageSize = 20;
}
