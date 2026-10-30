package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 停复牌记录。
 *
 * <p>表 {@code raw_data.tech_suspend_d}。
 *
 * <p>⚠️ {@code suspend_timing} 在表里是 {@code varchar(32)}（语义是「S=停牌 / R=复牌」代码），
 * <b>不是日期</b> → 必须用 {@code String}，用 {@code LocalDate} 会直接抛类型转换异常。
 */
@Data
@TableName("tech_suspend_d")
public class SuspendPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("trade_date")
    private LocalDate tradeDate;

    /** 停复牌状态代码（S=停牌 / R=复牌），表里是 varchar，不是日期 */
    @TableField("suspend_timing")
    private String suspendTiming;

    @TableField("suspend_type")
    private String suspendType;

    @TableField("data_source")
    private String dataSource;
}
