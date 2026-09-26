package com.attribution.interfaces.dto.kline;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineCollectRequest {

    @NotBlank
    private String symbol;

    @Min(1)
    @Max(3650)
    @Builder.Default
    private Integer days = 365;
}
