package com.attribution.application.service.indicator;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TechnicalSummary {

    private Double latestClose;
    private Double pctChange1d;
    private Double pctChange30d;

    private String maAlignment;
    private Double ma5;
    private Double ma10;
    private Double ma20;
    private Double ma60;
    private Boolean ma5AboveMa20;
    private Boolean goldenCrossRecent;

    private String macdStatus;
    private Double macdDif;
    private Double macdDea;
    private Double macdBar;

    private Double rsi6;
    private String rsiStatus;

    private Double kdjK;
    private Double kdjD;
    private Double kdjJ;
    private String kdjStatus;

    private Double bollUp;
    private Double bollMid;
    private Double bollDn;
    private String bollPosition;

    private List<String> signals;
}
