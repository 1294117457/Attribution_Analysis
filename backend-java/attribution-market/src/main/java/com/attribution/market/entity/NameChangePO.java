package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("tech_namechange")
public class NameChangePO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;
    private String name;

    @TableField("start_date")
    private LocalDate startDate;

    @TableField("end_date")
    private LocalDate endDate;

    @TableField("ann_date")
    private LocalDate annDate;

    @TableField("change_reason")
    private String changeReason;

    @TableField("data_source")
    private String dataSource;
}
