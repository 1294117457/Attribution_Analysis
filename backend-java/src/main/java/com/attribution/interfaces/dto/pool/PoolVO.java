package com.attribution.interfaces.dto.pool;

import com.attribution.domain.entity.StockPoolEntity;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolVO {

    private Long id;
    private String name;
    private String poolType;
    private String description;
    private String color;
    private String icon;
    private Integer sortOrder;
    private Boolean isDefault;
    private Boolean isArchived;
    private Integer memberCount;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static PoolVO fromEntity(StockPoolEntity e, int memberCount) {
        return PoolVO.builder()
            .id(e.getId())
            .name(e.getName())
            .poolType(e.getPoolType())
            .description(e.getDescription())
            .color(e.getColor())
            .icon(e.getIcon())
            .sortOrder(e.getSortOrder())
            .isDefault(e.getIsDefault())
            .isArchived(e.getIsArchived())
            .memberCount(memberCount)
            .createdAt(e.getCreatedAt())
            .updatedAt(e.getUpdatedAt())
            .build();
    }
}
