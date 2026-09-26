package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 概念同步参数
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptSyncRequest {

    /** 来源: tushare / akshare / both */
    @Builder.Default
    private String source = "both";

    /** 概念代码过滤 (为空表示全量) */
    private List<String> codes;

    /** 是否包含成分_*/
    @Builder.Default
    private Boolean includeMembers = true;
}
