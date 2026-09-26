package com.attribution.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
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
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(
    name = "stock_infos",
    indexes = {
        @Index(name = "ix_stock_infos_ts_code", columnList = "ts_code"),
        @Index(name = "ix_stock_infos_area", columnList = "area"),
        @Index(name = "ix_stock_infos_exchange", columnList = "exchange"),
        @Index(name = "ix_stock_infos_list_status", columnList = "list_status")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class StockInfoEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "symbol", nullable = false, unique = true, length = 10)
    private String symbol;

    @Column(name = "ts_code", length = 20)
    private String tsCode;

    @Column(name = "name", nullable = false, length = 100)
    private String name;

    @Column(name = "industry", length = 50)
    private String industry;

    @Column(name = "market", length = 20)
    private String market;

    @Column(name = "exchange", length = 10)
    private String exchange;

    @Column(name = "area", length = 50)
    private String area;

    @Column(name = "list_date")
    private LocalDate listDate;

    @Column(name = "delist_date")
    private LocalDate delistDate;

    @Column(name = "list_status", length = 5)
    @Builder.Default
    private String listStatus = "L";

    @Column(name = "is_hs", length = 5)
    @Builder.Default
    private String isHs = "N";

    @Column(name = "act_name", length = 200)
    private String actName;

    @Column(name = "act_ent_type", length = 50)
    private String actEntType;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
