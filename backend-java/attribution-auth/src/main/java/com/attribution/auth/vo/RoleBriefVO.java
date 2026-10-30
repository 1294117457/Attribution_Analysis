package com.attribution.auth.vo;

import lombok.Data;

/** 角色精简视图（嵌入 UserVO.roles） */
@Data
public class RoleBriefVO {
    private Integer id;
    private String code;
    private String name;
}
