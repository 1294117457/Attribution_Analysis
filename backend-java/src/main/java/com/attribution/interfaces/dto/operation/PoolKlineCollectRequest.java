package com.attribution.interfaces.dto.operation;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolKlineCollectRequest {

    @NotNull
    private Long poolId;

    @Builder.Default
    private String operationType = "kline_collect";

    @Min(1)
    @Builder.Default
    private Integer days = 365;
}
