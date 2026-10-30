package com.attribution.concept.entity;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 概念指数日线。
 *
 * <p>表 {@code raw_data.fundamental_concept_index}。
 *
 * <p>⚠️ {@code captured_at} 是 {@code timestamp with time zone} → 必须用 {@link OffsetDateTime}
 * （用 {@code LocalDateTime} 读 timestamptz 列会被 PG 驱动直接拒绝 → 查询 500）。
 */
@Data
@TableName("fundamental_concept_index")
public class ConceptIndexPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("index_code")
    private String indexCode;

    @TableField("concept_name")
    private String conceptName;

    @TableField("trade_date")
    private LocalDate tradeDate;

    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;

    private Long volume;
    private BigDecimal amount;
    private BigDecimal change;

    @TableField("change_pct")
    private BigDecimal changePct;

    /** 抓取时刻（timestamptz） */
    @TableField("captured_at")
    private OffsetDateTime capturedAt;
}
