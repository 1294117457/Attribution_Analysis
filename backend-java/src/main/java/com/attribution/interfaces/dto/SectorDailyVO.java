package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SectorDailyVO {

    private LocalDate tradeDate;
    private Double close;
    private Double open;
    private Double high;
    private Double low;
    private Double change;
    private Double pctChange;
    private Double amount;
    private Double vol;
    private Double turnoverRate;
}
