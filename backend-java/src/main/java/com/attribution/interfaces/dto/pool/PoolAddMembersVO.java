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
public class PoolAddMembersVO {

    private Long poolId;
    private List<String> added;
    private List<String> skipped;
    private Integer totalAdded;
    private Integer totalSkipped;
}
