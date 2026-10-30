package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_dividend")
public class DividendPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("end_date")
    private LocalDate endDate;

    @TableField("ann_date")
    private LocalDate annDate;

    @TableField("record_date")
    private LocalDate recordDate;

    @TableField("ex_date")
    private LocalDate exDate;

    @TableField("pay_date")
    private LocalDate payDate;

    @TableField("div_proc")
    private String divProc;

    @TableField("stk_div")
    private BigDecimal stkDiv;

    @TableField("stk_bo_rate")
    private BigDecimal stkBoRate;

    @TableField("stk_co_rate")
    private BigDecimal stkCoRate;

    @TableField("cash_div")
    private BigDecimal cashDiv;

    @TableField("cash_div_tax")
    private BigDecimal cashDivTax;

    @TableField("data_source")
    private String dataSource;
}
