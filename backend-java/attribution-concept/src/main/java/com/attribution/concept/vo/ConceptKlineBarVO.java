package com.attribution.concept.vo;

import java.math.BigDecimal;

import lombok.Data;

/** 概念日 K 单根 */
@Data
public class ConceptKlineBarVO {
    private String date;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private BigDecimal volume;
    private BigDecimal amount;
    private BigDecimal changePct;
    /** up / down / flat */
    private String color;
}
