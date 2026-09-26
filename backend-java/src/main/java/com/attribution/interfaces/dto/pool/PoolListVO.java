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
public class PoolListVO {

    private Integer total;
    private List<PoolVO> dataList;
}
