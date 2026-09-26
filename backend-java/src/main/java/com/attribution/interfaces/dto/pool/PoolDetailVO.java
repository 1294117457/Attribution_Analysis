package com.attribution.interfaces.dto.pool;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolDetailVO {

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
    private java.time.LocalDateTime createdAt;
    private java.time.LocalDateTime updatedAt;
    private List<PoolMemberVO> members;

    public static PoolDetailVO from(PoolVO pool, List<PoolMemberVO> members) {
        return PoolDetailVO.builder()
            .id(pool.getId())
            .name(pool.getName())
            .poolType(pool.getPoolType())
            .description(pool.getDescription())
            .color(pool.getColor())
            .icon(pool.getIcon())
            .sortOrder(pool.getSortOrder())
            .isDefault(pool.getIsDefault())
            .isArchived(pool.getIsArchived())
            .memberCount(pool.getMemberCount())
            .createdAt(pool.getCreatedAt())
            .updatedAt(pool.getUpdatedAt())
            .members(members)
            .build();
    }
}
