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
public class PoolPoolsBySymbolVO {

    private String symbol;
    private List<PoolVO> pools;
    private Integer total;
}
