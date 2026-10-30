package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("tech_trade_cal")
public class CalendarPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String exchange;

    @TableField("cal_date")
    private LocalDate calDate;

    @TableField("is_open")
    private Boolean isOpen;

    @TableField("pretrade_date")
    private LocalDate pretradeDate;

    @TableField("data_source")
    private String dataSource;
}
