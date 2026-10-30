package com.attribution.concept.entity;

import java.time.OffsetDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 概念板块。
 *
 * <p>表 {@code raw_data.fundamental_concept}。
 *
 * <p>⚠️ {@code first_seen_at} / {@code last_synced_at} 在表里是
 * {@code timestamp with time zone} → 必须用 {@link OffsetDateTime}
 * （用 {@code LocalDateTime} 读 timestamptz 列会被 PG 驱动直接拒绝 → 查询 500）。
 */
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

    /** 首次发现时间（timestamptz） */
    @TableField("first_seen_at")
    private OffsetDateTime firstSeenAt;

    /** 最近同步时间（timestamptz） */
    @TableField("last_synced_at")
    private OffsetDateTime lastSyncedAt;
}
