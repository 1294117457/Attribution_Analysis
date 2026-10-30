package com.attribution.user.vo;

import java.time.LocalDateTime;

import lombok.Data;

/** 自选池视图对象 */
@Data
public class PoolVO {
    private Integer id;
    private String name;
    private String poolType;
    private String description;
    private String color;
    private String icon;
    private Integer sortOrder;
    private Boolean isDefault;
    private Boolean isArchived;
    private Long memberCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
