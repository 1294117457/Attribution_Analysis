package com.attribution.market.vo;

import lombok.Data;

/** 删除 K 线结果 */
@Data
public class KlineDeleteVO {
    private String symbol;
    private Integer deletedCount;
    private String message;
}
