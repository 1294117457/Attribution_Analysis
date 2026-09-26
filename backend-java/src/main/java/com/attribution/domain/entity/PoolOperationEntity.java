package com.attribution.domain.entity;

import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.Type;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(
    name = "pool_operations",
    indexes = {
        @Index(name = "ix_pool_operations_type_status", columnList = "operation_type, status"),
        @Index(name = "ix_pool_operations_created_at", columnList = "created_at"),
        @Index(name = "ix_pool_operations_pool_time", columnList = "pool_id, created_at")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PoolOperationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "pool_id")
    private Long poolId;

    @Column(name = "operation_type", nullable = false, length = 32)
    private String operationType;

    @Column(name = "status", nullable = false, length = 16)
    @Builder.Default
    private String status = "pending";

    @Type(JsonType.class)
    @Column(name = "params", columnDefinition = "jsonb", nullable = false)
    @Builder.Default
    private Map<String, Object> params = new HashMap<>();

    @Type(JsonType.class)
    @Column(name = "result_summary", columnDefinition = "jsonb")
    private Map<String, Object> resultSummary;

    @Type(JsonType.class)
    @Column(name = "progress", columnDefinition = "jsonb", nullable = false)
    @Builder.Default
    private Map<String, Object> progress = new HashMap<>();

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "finished_at")
    private LocalDateTime finishedAt;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pool_id", insertable = false, updatable = false)
    private StockPoolEntity pool;
}
