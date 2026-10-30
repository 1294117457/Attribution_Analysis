package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_stock_basic")
public class StockInfoPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("ts_code")
    private String tsCode;

    private String name;
    private String area;
    private String industry;
    private String market;
    private String exchange;

    @TableField("list_date")
    private LocalDate listDate;

    @TableField("delist_date")
    private LocalDate delistDate;

    @TableField("list_status")
    private String listStatus;

    @TableField("is_hs")
    private String isHs;

    @TableField("total_shares")
    private Long totalShares;

    @TableField("act_name")
    private String actName;

    @TableField("act_ent_type")
    private String actEntType;
}
