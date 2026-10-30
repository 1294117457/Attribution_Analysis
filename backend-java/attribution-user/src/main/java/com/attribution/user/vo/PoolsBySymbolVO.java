package com.attribution.user.vo;

import java.util.List;

import lombok.Data;

/** 按股票代码反查所属池 */
@Data
public class PoolsBySymbolVO {
    private String symbol;
    private List<PoolVO> pools;
    private Integer total;
}
