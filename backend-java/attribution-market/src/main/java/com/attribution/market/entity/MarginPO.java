package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_margin")
public class MarginPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("trade_date")
    private LocalDate tradeDate;

    @TableField("exchange_id")
    private String exchangeId;

    private BigDecimal rzye;
    private BigDecimal rzmre;
    private BigDecimal rzche;
    private BigDecimal rqye;
    private BigDecimal rqmcl;
    private BigDecimal rzrqye;
    private BigDecimal rqyl;

    @TableField("data_source")
    private String dataSource;
}
