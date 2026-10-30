package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 股票基础信息。
 *
 * <p>表 {@code raw_data.fundamental_stock_basic}（**采集库** raw_data）。
 *
 * <p>⚠️ 该表由 Collector 独占写入，Java **只读**。
 */
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

    /** 公司全称 */
    @TableField("fullname")
    private String fullname;

    /** 英文名称 */
    @TableField("enname")
    private String enname;

    /** 拼音缩写 */
    @TableField("cnspell")
    private String cnspell;

    /** 货币类型 */
    @TableField("curr_type")
    private String currType;
}
