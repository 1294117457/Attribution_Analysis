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
    name = "mkt_index_members",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_mkt_index_members_uk",
            columnNames = {"sector_type", "sector_code", "symbol", "effective_date"})
    },
    indexes = {
        @Index(name = "ix_mkt_index_members_sector", columnList = "sector_type, sector_code")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class MktIndexMemberEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "sector_type", nullable = false, length = 16)
    private String sectorType;

    @Column(name = "sector_code", nullable = false, length = 32)
    private String sectorCode;

    @Column(name = "sector_name", length = 64)
    private String sectorName;

    @Column(name = "symbol", nullable = false, length = 10)
    private String symbol;

    @Column(name = "name", length = 50)
    private String name;

    @Column(name = "effective_date")
    private LocalDate effectiveDate;

    @Column(name = "expiry_date")
    private LocalDate expiryDate;

    @Column(name = "is_new", length = 8)
    private String isNew;

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
