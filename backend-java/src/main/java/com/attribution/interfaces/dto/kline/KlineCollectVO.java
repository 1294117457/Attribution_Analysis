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
public class KlineCollectVO {

    private String symbol;
    private Integer fetched;
    private Integer saved;
    private LocalDate startDate;
    private LocalDate endDate;
    private String message;
}
