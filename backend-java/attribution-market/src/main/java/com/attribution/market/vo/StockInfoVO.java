package com.attribution.market.vo;

import lombok.Data;

/** 股票基础信息视图对象（对应前端 StockInfo） */
@Data
public class StockInfoVO {
    private String symbol;
    private String tsCode;
    private String name;
    private String area;
    private String industry;
    private String market;
    private String exchange;
    /** 上市日期 YYYYMMDD */
    private String listDate;
    private String delistDate;
    private String listStatus;
    private String isHs;
    private String actName;
    private String actEntType;
    private Long totalShares;
    /** 公司全称 */
    private String fullname;
    /** 英文名称 */
    private String enname;
    /** 拼音缩写 */
    private String cnspell;
    /** 货币类型 */
    private String currType;
}
