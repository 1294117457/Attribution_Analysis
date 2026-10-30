package com.attribution.auth.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("sys_roles")
public class RolePO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String code;
    private String name;
    private String description;

    @TableField("is_system")
    private Boolean isSystem;

    @TableField("sort_order")
    private Integer sortOrder;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
