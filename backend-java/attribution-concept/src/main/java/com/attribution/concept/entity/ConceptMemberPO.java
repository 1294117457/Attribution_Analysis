package com.attribution.concept.entity;

import java.time.OffsetDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 概念成分股。
 *
 * <p>表 {@code raw_data.fundamental_concept_member}。
 *
 * <p>⚠️ {@code joined_at} / {@code synced_at} 在表里是 {@code timestamp with time zone}
 * → 必须用 {@link OffsetDateTime}（用 {@code LocalDateTime} 读 timestamptz 列会被 PG 驱动直接拒绝 → 查询 500）。
 *
 * <p>⚠️ 该表**没有主键列**（只有 symbol + concept_id 联合唯一），故不加 {@code @TableId}。
 */
@Data
@TableName("fundamental_concept_member")
public class ConceptMemberPO {
    private String symbol;

    @TableField("concept_id")
    private Integer conceptId;

    private String reason;

    /** 纳入时间（timestamptz） */
    @TableField("joined_at")
    private OffsetDateTime joinedAt;

    /** 同步时间（timestamptz） */
    @TableField("synced_at")
    private OffsetDateTime syncedAt;

    private String source;

    /** 简称 */
    @TableField("short_name")
    private String shortName;
}
