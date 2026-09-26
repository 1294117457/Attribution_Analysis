package com.attribution.interfaces.dto.operation;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolOperationCreateVO {

    private Long operationId;
    private Long poolId;
    private String operationType;
    private String status;
    private Integer total;
    private String message;
}
