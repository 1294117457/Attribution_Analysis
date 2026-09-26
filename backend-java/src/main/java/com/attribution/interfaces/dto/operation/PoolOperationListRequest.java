package com.attribution.interfaces.dto.operation;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolOperationListRequest {

    private Long poolId;
    private Integer limit;
    private Integer offset;
}
