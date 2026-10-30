package com.attribution.user.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("stock_pools")
public class StockPoolPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String name;
    private String description;

    @TableField("pool_type")
    private String poolType;

    private String color;
    private String icon;

    @TableField("sort_order")
    private Integer sortOrder;

    @TableField("is_default")
    private Boolean isDefault;

    @TableField("is_archived")
    private Boolean isArchived;

    @TableField("owner_id")
    private Integer ownerId;

    @TableField("share_token")
    private String shareToken;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
