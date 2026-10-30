package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_moneyflow")
public class MoneyflowPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("trade_date")
    private LocalDate tradeDate;

    @TableField("buy_sm_vol")
    private BigDecimal buySmVol;

    @TableField("buy_sm_amount")
    private BigDecimal buySmAmount;

    @TableField("sell_sm_vol")
    private BigDecimal sellSmVol;

    @TableField("sell_sm_amount")
    private BigDecimal sellSmAmount;

    @TableField("buy_md_vol")
    private BigDecimal buyMdVol;

    @TableField("buy_md_amount")
    private BigDecimal buyMdAmount;

    @TableField("sell_md_vol")
    private BigDecimal sellMdVol;

    @TableField("sell_md_amount")
    private BigDecimal sellMdAmount;

    @TableField("buy_lg_vol")
    private BigDecimal buyLgVol;

    @TableField("buy_lg_amount")
    private BigDecimal buyLgAmount;

    @TableField("sell_lg_vol")
    private BigDecimal sellLgVol;

    @TableField("sell_lg_amount")
    private BigDecimal sellLgAmount;

    @TableField("buy_elg_vol")
    private BigDecimal buyElgVol;

    @TableField("buy_elg_amount")
    private BigDecimal buyElgAmount;

    @TableField("sell_elg_vol")
    private BigDecimal sellElgVol;

    @TableField("sell_elg_amount")
    private BigDecimal sellElgAmount;

    @TableField("net_mf_vol")
    private BigDecimal netMfVol;

    @TableField("net_mf_amount")
    private BigDecimal netMfAmount;

    @TableField("data_source")
    private String dataSource;
}
