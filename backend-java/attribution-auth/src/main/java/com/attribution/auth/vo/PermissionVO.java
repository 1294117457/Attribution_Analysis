package com.attribution.auth.vo;

import lombok.Data;

/** 权限视图对象 */
@Data
public class PermissionVO {
    private Integer id;
    private String code;
    private String resource;
    private String action;
    private String name;
    private String description;
}
