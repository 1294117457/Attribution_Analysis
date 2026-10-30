package com.attribution.market.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("capital_stk_holdernumber")
public class HolderNumPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String symbol;

    @TableField("ann_date")
    private LocalDate annDate;

    @TableField("end_date")
    private LocalDate endDate;

    @TableField("holder_num")
    private Integer holderNum;

    @TableField("holder_nums")
    private BigDecimal holderNums;

    @TableField("data_source")
    private String dataSource;
}
