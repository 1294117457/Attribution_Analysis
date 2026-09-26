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
public class PoolMemberListVO {

    private Long poolId;
    private Integer total;
    private List<PoolMemberVO> dataList;
}
