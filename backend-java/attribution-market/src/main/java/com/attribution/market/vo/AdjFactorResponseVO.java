package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 复权因子响应 */
@Data
public class AdjFactorResponseVO {
    private String symbol;
    private List<AdjFactorVO> factors;
}
