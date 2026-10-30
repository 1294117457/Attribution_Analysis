package com.attribution.concept.vo;

import java.util.List;

import lombok.Data;

/** 概念 K 线完整响应 */
@Data
public class ConceptKlineResponseVO {
    private List<ConceptKlineBarVO> kline;
    private ConceptSnapshotVO realtime;
    private ConceptKlineMetaVO meta;
    private ConceptDataRangeVO dataRange;
}
