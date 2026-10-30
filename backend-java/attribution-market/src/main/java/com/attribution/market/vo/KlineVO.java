package com.attribution.market.vo;

import java.math.BigDecimal;

import lombok.Data;

/**
 * K 线视图对象（含 17 个技术指标列）。
 *
 * <p>对应前端 {@code Kline}（stock-info/api.ts）。
 */
@Data
public class KlineVO {
    private String symbol;
    private String name;
    private String date;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Integer volume;
    private BigDecimal amount;
    private BigDecimal changePct;

    // ── 均线 ──
    private Double ma5;
    private Double ma10;
    private Double ma20;
    private Double ma60;

    // ── EMA ──
    private Double ema12;
    private Double ema26;

    // ── MACD ──
    private Double macdDif;
    private Double macdDea;
    private Double macdBar;

    // ── RSI ──
    private Double rsi6;
    private Double rsi12;
    private Double rsi24;

    // ── KDJ ──
    private Double kdjK;
    private Double kdjD;
    private Double kdjJ;

    // ── BOLL ──
    private Double bollUp;
    private Double bollMid;
    private Double bollDn;
}
