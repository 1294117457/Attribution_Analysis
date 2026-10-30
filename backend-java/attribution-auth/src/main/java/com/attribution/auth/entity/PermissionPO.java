package com.attribution.auth.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("sys_permissions")
public class PermissionPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String code;
    private String resource;
    private String action;
    private String name;
    private String description;

    @TableField("created_at")
    private LocalDateTime createdAt;
}
