package com.attribution.market.vo;

import java.time.LocalDate;

import lombok.Data;

/** 曾用名变更记录 */
@Data
public class NameChangeVO {
    private String name;
    private LocalDate startDate;
    private LocalDate endDate;
    private LocalDate annDate;
    private String changeReason;
}
