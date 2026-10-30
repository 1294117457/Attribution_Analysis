package com.attribution.concept.converter;

import java.util.List;

import com.attribution.concept.entity.ConceptPO;
import com.attribution.concept.vo.ConceptBriefVO;
import com.attribution.concept.vo.ConceptVO;

/** 概念 PO → VO 转换器 */
public final class ConceptConverter {

    private ConceptConverter() {
    }

    /** 概念类型展示标签 */
    public static final java.util.Map<String, String> TYPE_LABELS =
            java.util.Map.of(
                    "industry", "行业概念",
                    "theme", "主题概念",
                    "style", "风格概念",
                    "region", "地域概念",
                    "event", "事件概念",
                    "other", "其他概念");

    public static String typeLabel(String conceptType) {
        String type = conceptType == null ? "other" : conceptType;
        return TYPE_LABELS.getOrDefault(type, type);
    }

    public static ConceptVO toVO(ConceptPO po) {
        if (po == null) return null;
        ConceptVO vo = new ConceptVO();
        vo.setConceptId(po.getId());
        vo.setIndexCode(po.getIndexCode());
        vo.setName(po.getName());
        vo.setSource(po.getSource());
        vo.setConceptType(po.getConceptType() == null ? "other" : po.getConceptType());
        vo.setStockCount(po.getStockCount());
        vo.setDescription(po.getDescription());
        vo.setIsActive(po.getIsActive());
        vo.setLastSyncedAt(po.getLastSyncedAt());
        vo.setFirstSeenAt(po.getFirstSeenAt());
        return vo;
    }

    public static List<ConceptVO> toVOList(List<ConceptPO> pos) {
        return pos == null ? List.of() : pos.stream().map(ConceptConverter::toVO).toList();
    }

    public static ConceptBriefVO toBriefVO(ConceptPO po) {
        if (po == null) return null;
        ConceptBriefVO vo = new ConceptBriefVO();
        vo.setConceptId(po.getId());
        vo.setName(po.getName());
        vo.setSource(po.getSource() == null ? "ths" : po.getSource());
        vo.setConceptType(po.getConceptType() == null ? "other" : po.getConceptType());
        return vo;
    }
}
