package com.attribution.user.vo;

import java.time.LocalDateTime;

import lombok.Data;

/** 池成员视图对象（含股票基础信息，来自 fundamental_stock_info 联表） */
@Data
public class PoolMemberVO {
    private String symbol;
    private String memo;
    private Integer sortOrder;
    private LocalDateTime addedAt;
    private String name;
    private String industry;
    private String market;
    private String exchange;
    /** 股票是否存在（false 表示该代码在基础信息表中无记录） */
    private Boolean isValid;
}
