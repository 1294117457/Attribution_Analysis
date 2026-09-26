package com.attribution.interfaces.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 概念简_- 用于面板和股票详情抽屉中的轻量展_
 *
 * 前端字段：concept_id / name / source（api.ts 旧定义）
 * 后端存储：concepts 表只有 id (Bigint)，无 concept_code 数字主键 → 直接用 id
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptBriefVO {

    /** 概念 id（前端 StockInfo.concepts[].concept_id） */
    @JsonProperty("concept_id") private String conceptId;

    /** 概念名称 */
    @JsonProperty("name")       private String name;

    /** 来源标签: em / ths */
    @JsonProperty("source")     private String source;

    /** 兼容旧字段 code（id.toString()） */
    @JsonProperty("code")       private String code;
}
