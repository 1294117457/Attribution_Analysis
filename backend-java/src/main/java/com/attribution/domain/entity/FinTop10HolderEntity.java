package com.attribution.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "fin_top10_holders",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_fin_top10_holders_uk",
            columnNames = {"symbol", "end_date", "ann_date", "holder_name"})
    },
    indexes = {
        @Index(name = "ix_fin_top10_holders_date", columnList = "end_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FinTop10HolderEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "ann_date")
    private LocalDate annDate;

    @Column(name = "end_date")
    private LocalDate endDate;

    @Column(name = "holder_name", nullable = false, length = 128)
    private String holderName;

    @Column(name = "hold_amount")
    private Double holdAmount;

    @Column(name = "hold_ratio")
    private Double holdRatio;

    @Column(name = "hold_float_ratio")
    private Double holdFloatRatio;

    @Column(name = "hold_change")
    private Double holdChange;

    @Column(name = "holder_type", length = 32)
    private String holderType;

    @Column(name = "data_source", nullable = false, length = 16)
    @Builder.Default
    private String dataSource = "tushare";

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
