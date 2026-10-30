package com.attribution.concept.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import lombok.Data;

/** 概念成员分页查询条件 */
@Data
public class ConceptMemberQuery {
    @NotNull(message = "概念 ID 不能为空")
    private Integer conceptId;

    /** pct_change / latest_close / total_mv / name */
    private String sortBy;

    /** asc / desc */
    private String sortOrder = "desc";

    /** 是否附带所属自选池 */
    private boolean withPools = false;

    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 200, message = "每页条数最多 200")
    private int pageSize = 20;
}
