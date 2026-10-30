package com.attribution.market.vo;

import java.math.BigDecimal;

import lombok.Data;

/** 看板 K 线单根（与技术指标列） */
@Data
public class MarketKlineVO {
    private String tradeDate;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Integer volume;
    private BigDecimal amount;
    private BigDecimal changePct;

    // ── 技术指标 ──
    private Double ma5;
    private Double ma10;
    private Double ma20;
    private Double ma60;
    private Double ema12;
    private Double ema26;
    private Double macdDif;
    private Double macdDea;
    private Double macdBar;
    private Double rsi6;
    private Double rsi12;
    private Double rsi24;
    private Double kdjK;
    private Double kdjD;
    private Double kdjJ;
    private Double bollUp;
    private Double bollMid;
    private Double bollDn;
}
