package com.attribution.interfaces.dto.kline;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineQueryRequest {

    private String symbol;

    private LocalDate startDate;

    private LocalDate endDate;

    @Min(1)
    @Max(3650)
    @Builder.Default
    private Integer limit = 365;

    @Builder.Default
    private Boolean orderDesc = true;
}
