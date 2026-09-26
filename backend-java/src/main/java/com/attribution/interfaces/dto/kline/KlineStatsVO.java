package com.attribution.interfaces.dto.kline;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KlineStatsVO {

    private String symbol;
    private Long totalCount;
    private LocalDate firstDate;
    private LocalDate lastDate;
    private Double latestClose;
}
