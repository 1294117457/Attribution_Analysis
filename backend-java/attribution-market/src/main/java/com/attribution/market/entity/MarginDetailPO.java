package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_margin_detail")
public class MarginDetailPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private BigDecimal rzye;
    private BigDecimal rqye;
    private BigDecimal rzmre;
    private BigDecimal rqyl;
    private BigDecimal rzche;
    private BigDecimal rqchl;
    private BigDecimal rqmcl;
    private BigDecimal rzrqye;

    @TableField("data_source")
    private String dataSource;
}
