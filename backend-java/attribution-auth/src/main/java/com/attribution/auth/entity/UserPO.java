package com.attribution.auth.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("sys_users")
public class UserPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    private String email;
    private String username;

    @TableField("password_hash")
    private String passwordHash;

    private String nickname;

    @TableField("avatar_url")
    private String avatarUrl;

    @TableField("is_active")
    private Boolean isActive;

    @TableField("is_verified")
    private Boolean isVerified;

    @TableField("last_login_at")
    private LocalDateTime lastLoginAt;

    @TableField("last_login_ip")
    private String lastLoginIp;

    @TableField("created_at")
    private LocalDateTime createdAt;

    @TableField("updated_at")
    private LocalDateTime updatedAt;
}
