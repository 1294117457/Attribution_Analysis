package com.attribution.market.vo;

import java.math.BigDecimal;
import java.time.LocalDate;

import lombok.Data;

/** 融资融券明细（单日） */
@Data
public class MarginDayVO {
    private LocalDate tradeDate;
    private BigDecimal rzye;
    private BigDecimal rqye;
    private BigDecimal rzrqye;
    private BigDecimal rzmre;
    private BigDecimal rzche;
    private BigDecimal rqyl;
    private BigDecimal rqmcl;
    private BigDecimal rqchl;
}
