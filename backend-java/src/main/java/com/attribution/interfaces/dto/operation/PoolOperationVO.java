package com.attribution.interfaces.dto.operation;

import com.attribution.domain.entity.PoolOperationEntity;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolOperationVO {

    private Long id;
    private Long poolId;
    private String operationType;
    private String status;
    private Map<String, Object> params;
    private Map<String, Object> resultSummary;
    private PoolOperationProgressVO progress;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime finishedAt;
    private LocalDateTime createdAt;

    public static PoolOperationVO fromEntity(PoolOperationEntity e) {
        Map<String, Object> progressMap = e.getProgress() != null ? e.getProgress() : new HashMap<>();
        PoolOperationProgressVO progress = PoolOperationProgressVO.builder()
            .done(asInt(progressMap.get("done")))
            .total(asInt(progressMap.get("total")))
            .failed(asInt(progressMap.get("failed")))
            .build();

        return PoolOperationVO.builder()
            .id(e.getId())
            .poolId(e.getPoolId())
            .operationType(e.getOperationType())
            .status(e.getStatus())
            .params(e.getParams())
            .resultSummary(e.getResultSummary())
            .progress(progress)
            .errorMessage(e.getErrorMessage())
            .startedAt(e.getStartedAt())
            .finishedAt(e.getFinishedAt())
            .createdAt(e.getCreatedAt())
            .build();
    }

    private static Integer asInt(Object v) {
        if (v == null) return 0;
        if (v instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(v.toString());
        } catch (Exception ex) {
            return 0;
        }
    }
}
