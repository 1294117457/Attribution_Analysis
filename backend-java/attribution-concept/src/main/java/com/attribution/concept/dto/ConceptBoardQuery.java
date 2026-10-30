package com.attribution.concept.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** 概念大盘查询条件 */
@Data
public class ConceptBoardQuery {
    /** all / industry / theme / style / region / event / other */
    private String typeFilter = "all";

    /** pct_change / stock_count / name */
    private String sortBy;

    /** asc / desc */
    private String sortOrder = "desc";

    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 500, message = "每页条数最多 500")
    private int pageSize = 20;
}
