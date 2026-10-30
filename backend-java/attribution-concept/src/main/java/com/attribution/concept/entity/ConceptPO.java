package com.attribution.concept.entity;

import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_concept")
public class ConceptPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("index_code")
    private String indexCode;

    @TableField("concept_code")
    private String conceptCode;

    private String name;
    private String source;

    @TableField("concept_type")
    private String conceptType;

    private String description;

    @TableField("stock_count")
    private Integer stockCount;

    @TableField("is_active")
    private Boolean isActive;

    @TableField("first_seen_at")
    private LocalDateTime firstSeenAt;

    @TableField("last_synced_at")
    private LocalDateTime lastSyncedAt;
}
