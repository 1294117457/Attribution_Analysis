package com.attribution.concept.entity;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

/**
 * 概念板块实时快照。
 *
 * <p>表 {@code raw_data.fundamental_concept_snapshot}。
 *
 * <p>⚠️ 时间列类型：
 * <ul>
 *   <li>{@code trade_time} 是 naive {@code timestamp without time zone} → 用 {@link LocalDateTime}；</li>
 *   <li>{@code captured_at} 是 {@code timestamp with time zone} → 必须用 {@link OffsetDateTime}
 *       （用 {@code LocalDateTime} 读 timestamptz 列会被 PG 驱动直接拒绝 → 查询 500）。</li>
 * </ul>
 */
@Data
@TableName("fundamental_concept_snapshot")
public class ConceptSnapshotPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("index_code")
    private String indexCode;

    @TableField("concept_name")
    private String conceptName;

    /** 交易时刻（naive timestamp） */
    @TableField("trade_time")
    private LocalDateTime tradeTime;

    /** 交易日（date） */
    @TableField("trade_date")
    private LocalDate tradeDate;

    @TableField("open_price")
    private BigDecimal openPrice;

    private BigDecimal high;
    private BigDecimal low;

    private BigDecimal price;

    @TableField("prev_close")
    private BigDecimal prevClose;

    /** 涨跌幅（pct_change） */
    @TableField("pct_change")
    private BigDecimal pctChange;

    /** 涨跌额（p_change） */
    @TableField("p_change")
    private BigDecimal pChange;

    @TableField("rank_current")
    private Integer rankCurrent;

    @TableField("rank_total")
    private Integer rankTotal;

    @TableField("up_count")
    private Integer upCount;

    @TableField("down_count")
    private Integer downCount;

    @TableField("volume_wan")
    private BigDecimal volumeWan;

    @TableField("turnover_yi")
    private BigDecimal turnoverYi;

    @TableField("net_inflow_yi")
    private BigDecimal netInflowYi;

    private String source;

    /** 抓取时刻（timestamptz） */
    @TableField("captured_at")
    private OffsetDateTime capturedAt;
}
