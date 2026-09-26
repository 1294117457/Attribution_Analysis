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
public class DividendVO {

    private LocalDate endDate;
    private LocalDate exDate;
    private LocalDate payDate;
    private Double cashDiv;
    private Double cashDivTax;
    private Double stkDiv;
    private String divProc;
}
