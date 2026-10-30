package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("tech_adj_factor")
public class AdjFactorPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("trade_date")
    private LocalDate tradeDate;

    @TableField("adj_factor")
    private BigDecimal adjFactor;

    @TableField("data_source")
    private String dataSource;
}
