package com.attribution.interfaces.dto.pool;

import com.attribution.domain.entity.StockPoolMemberEntity;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolMemberVO {

    private String symbol;
    private String memo;
    private Integer sortOrder;
    private String name;
    private String industry;
    private String market;
    private String exchange;
    private Boolean isValid;
    private LocalDateTime addedAt;

    public static PoolMemberVO fromEntity(StockPoolMemberEntity e) {
        return PoolMemberVO.builder()
            .symbol(e.getSymbol())
            .memo(e.getMemo())
            .sortOrder(e.getSortOrder())
            .addedAt(e.getAddedAt())
            .isValid(true)
            .build();
    }
}
