package com.attribution.interfaces.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/** 股票所属池的简略视图（嵌在 StockPanelRowVO.pools） */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolBriefVO {

    @JsonProperty("pool_id")   private Long poolId;
    @JsonProperty("name")      private String name;
    @JsonProperty("pool_type") private String poolType;
    @JsonProperty("joined_at") private LocalDateTime joinedAt;
}
