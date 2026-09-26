package com.attribution.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;

/**
 * 概念聚合根 - 表名 concepts，与数据库实际 schema 对齐：
 *   id, name, source, concept_type, description, stock_count,
 *   is_active, first_seen_at, last_synced_at
 *
 * 注意：DB 没有 concept_code / concept_name / market / created_at / updated_at 列。
 * 前端概念 code 用 id.toString() 表达。
 */
@Entity
@Table(
    name = "concepts",
    indexes = {
        @Index(name = "ix_concepts_source", columnList = "source")
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ConceptEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "name", nullable = false, length = 100)
    private String name;

    @Column(name = "source", nullable = false, length = 10)
    @Builder.Default
    private String source = "em";

    @Column(name = "concept_type", nullable = false, length = 50)
    @Builder.Default
    private String conceptType = "other";

    @Column(name = "description", columnDefinition = "text")
    private String description;

    @Column(name = "stock_count", nullable = false)
    @Builder.Default
    private Integer stockCount = 0;

    @Column(name = "is_active", nullable = false)
    @Builder.Default
    private Boolean isActive = true;

    @JdbcTypeCode(SqlTypes.TIMESTAMP_WITH_TIMEZONE)
    @Column(name = "first_seen_at", nullable = false)
    private OffsetDateTime firstSeenAt;

    @JdbcTypeCode(SqlTypes.TIMESTAMP_WITH_TIMEZONE)
    @Column(name = "last_synced_at")
    private OffsetDateTime lastSyncedAt;

    /** 前端展示用: code (id 字符串化) */
    public String getCode() {
        return id == null ? null : id.toString();
    }
}
