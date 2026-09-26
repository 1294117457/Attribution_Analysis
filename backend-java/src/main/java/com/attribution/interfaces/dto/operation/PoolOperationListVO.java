package com.attribution.interfaces.dto.operation;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PoolOperationListVO {

    private Long poolId;
    private Integer total;
    private List<PoolOperationVO> dataList;
}
