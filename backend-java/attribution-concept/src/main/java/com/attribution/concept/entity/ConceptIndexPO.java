package com.attribution.concept.entity;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.*;

import lombok.Data;

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

    @TableField("captured_at")
    private LocalDateTime capturedAt;
}
