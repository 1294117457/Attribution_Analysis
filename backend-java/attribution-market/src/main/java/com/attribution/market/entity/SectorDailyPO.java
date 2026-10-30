package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_sector_daily")
public class SectorDailyPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("sector_type")
    private String sectorType;

    @TableField("sector_code")
    private String sectorCode;

    @TableField("sector_name")
    private String sectorName;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private BigDecimal close;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;

    @TableField("pre_close")
    private BigDecimal preClose;

    private BigDecimal change;

    @TableField("pct_change")
    private BigDecimal pctChange;

    private BigDecimal vol;
    private BigDecimal amount;

    @TableField("turnover_rate")
    private BigDecimal turnoverRate;

    @TableField("data_source")
    private String dataSource;
}
