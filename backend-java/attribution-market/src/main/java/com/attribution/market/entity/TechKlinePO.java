package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("tech_daily")
public class TechKlinePO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;
    private String name;
    private LocalDate date;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Integer volume;
    private BigDecimal amount;

    @TableField("change_pct")
    private BigDecimal changePct;
}
