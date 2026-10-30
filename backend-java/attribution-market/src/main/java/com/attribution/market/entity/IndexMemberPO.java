package com.attribution.market.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_index_member")
public class IndexMemberPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("sector_type")
    private String sectorType;

    @TableField("sector_code")
    private String sectorCode;

    @TableField("sector_name")
    private String sectorName;

    private String symbol;
    private String name;

    @TableField("effective_date")
    private LocalDate effectiveDate;

    @TableField("expiry_date")
    private LocalDate expiryDate;

    @TableField("is_new")
    private String isNew;

    @TableField("data_source")
    private String dataSource;
}
