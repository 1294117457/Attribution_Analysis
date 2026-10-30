package com.attribution.concept.entity;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

@Data
@TableName("fundamental_concept_snapshot")
public class ConceptSnapshotPO {
    @TableId(type = IdType.AUTO)
    private Integer id;

    @TableField("index_code")
    private String indexCode;

    @TableField("concept_name")
    private String conceptName;

    @TableField("trade_time")
    private LocalDateTime tradeTime;

    @TableField("open_price")
    private BigDecimal openPrice;

    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal price;

    @TableField("prev_close")
    private BigDecimal prevClose;

    @TableField("pct_change")
    private BigDecimal pctChange;

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

    @TableField("captured_at")
    private LocalDateTime capturedAt;
}
