package com.attribution.auth.vo;

import lombok.Data;

/** 角色视图对象 */
@Data
public class RoleVO {
    private Integer id;
    private String code;
    private String name;
    private String description;
    private Boolean isSystem;
    private Integer sortOrder;
}
