package com.attribution.user.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("stock_pool_members")
public class PoolMemberPO {
    @TableField("pool_id")
    private Integer poolId;

    private String symbol;
    private String memo;

    @TableField("sort_order")
    private Integer sortOrder;

    @TableField("added_at")
    private LocalDateTime addedAt;
}
