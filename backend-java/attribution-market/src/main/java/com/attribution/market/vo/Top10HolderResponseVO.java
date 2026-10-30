package com.attribution.market.vo;

import java.util.List;

import lombok.Data;

/** 十大股东响应 */
@Data
public class Top10HolderResponseVO {
    private String symbol;
    private List<Top10HolderRowVO> holders;
}
