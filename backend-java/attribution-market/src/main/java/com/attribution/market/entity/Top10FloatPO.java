package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_top10_floatholders")
public class Top10FloatPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("ann_date")
    private LocalDate annDate;

    @TableField("end_date")
    private LocalDate endDate;

    @TableField("holder_name")
    private String holderName;

    @TableField("hold_amount")
    private BigDecimal holdAmount;

    @TableField("hold_ratio")
    private BigDecimal holdRatio;

    @TableField("hold_change")
    private BigDecimal holdChange;

    @TableField("holder_type")
    private String holderType;

    @TableField("data_source")
    private String dataSource;
}
