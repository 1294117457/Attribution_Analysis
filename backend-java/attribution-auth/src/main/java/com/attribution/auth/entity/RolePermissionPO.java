package com.attribution.auth.entity;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("sys_role_permissions")
public class RolePermissionPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("role_id")
    private Integer roleId;

    @TableField("permission_id")
    private Integer permissionId;
}
