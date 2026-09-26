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
    name = "cap_margins",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_cap_margins_uk", columnNames = {"exchange_id", "trade_date"})
    },
    indexes = {
        @Index(name = "ix_cap_margins_date", columnList = "trade_date")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CapMarginEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "trade_date", nullable = false)
    private LocalDate tradeDate;

    @Column(name = "exchange_id", nullable = false, length = 16)
    private String exchangeId;

    @Column(name = "rzye")
    private Double rzye;

    @Column(name = "rzmre")
    private Double rzmre;

    @Column(name = "rzche")
    private Double rzche;

    @Column(name = "rqye")
    private Double rqye;

    @Column(name = "rqmcl")
    private Double rqmcl;

    @Column(name = "rzrqye")
    private Double rzrqye;

    @Column(name = "rqyl")
    private Double rqyl;

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
