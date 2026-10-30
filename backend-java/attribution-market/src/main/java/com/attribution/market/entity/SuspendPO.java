package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("tech_suspend_d")
public class SuspendPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("trade_date")
    private LocalDate tradeDate;

    @TableField("suspend_timing")
    private LocalDate suspendTiming;

    @TableField("suspend_type")
    private String suspendType;

    @TableField("data_source")
    private String dataSource;
}
