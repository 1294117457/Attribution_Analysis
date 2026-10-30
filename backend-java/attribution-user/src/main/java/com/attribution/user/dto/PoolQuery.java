package com.attribution.user.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;

import lombok.Data;

/** 池列表查询条件 */
@Data
public class PoolQuery {
    private boolean includeArchived = false;

    @Min(value = 1, message = "页码需大于 0")
    private int page = 1;

    @Min(value = 1, message = "每页条数需大于 0")
    @Max(value = 500, message = "每页条数最多 500")
    private int pageSize = 100;
}
