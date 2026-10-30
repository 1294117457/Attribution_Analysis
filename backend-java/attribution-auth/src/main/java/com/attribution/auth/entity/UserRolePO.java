package com.attribution.auth.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("sys_user_roles")
public class UserRolePO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("user_id")
    private Integer userId;

    @TableField("role_id")
    private Integer roleId;

    @TableField("granted_at")
    private LocalDateTime grantedAt;

    @TableField("granted_by")
    private Integer grantedBy;
}
