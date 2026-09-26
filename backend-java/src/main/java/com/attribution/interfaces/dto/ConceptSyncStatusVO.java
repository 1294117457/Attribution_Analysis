package com.attribution.interfaces.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptSyncStatusVO {

    private String source;
    private Long lastTaskId;
    private String lastStatus;
    private String lastMessage;
    private String lastStartedAt;
    private String lastFinishedAt;
    private Integer lastTotal;
    private Integer lastSuccess;
    private Integer lastFail;
    /** 历史是否曾执行过同步 */
    private Boolean hasHistory;
}
