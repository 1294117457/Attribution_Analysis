package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/**
 * 技术形态摘要视图对象。
 *
 * <p>对应前端 {@code TechnicalSummary}（stock-info/api.ts）。
 */
@Data
public class TechnicalSummaryVO {
    private Double latestClose;
    private Double pctChange1d;
    private Double pctChange30d;
    /** bullish / bearish / neutral */
    private String maAlignment;
    private Double ma5;
    private Double ma10;
    private Double ma20;
    private Double ma60;
    private Boolean ma5AboveMa20;
    private Boolean goldenCrossRecent;
    /** golden_cross / death_cross / above_zero / below_zero / neutral */
    private String macdStatus;
    private Double macdDif;
    private Double macdDea;
    private Double macdBar;
    private Double rsi6;
    /** overbought / oversold / neutral */
    private String rsiStatus;
    private Double kdjK;
    private Double kdjD;
    private Double kdjJ;
    /** golden_cross / death_cross / overbought / oversold / neutral */
    private String kdjStatus;
    private Double bollUp;
    private Double bollMid;
    private Double bollDn;
    /** above_upper / below_lower / upper_half / lower_half / middle */
    private String bollPosition;
    /** 形态信号文案列表 */
    private List<String> signals;
}
