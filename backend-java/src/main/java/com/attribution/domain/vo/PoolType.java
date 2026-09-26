package com.attribution.domain.vo;

import lombok.Getter;

@Getter
public enum PoolType {

    WATCHLIST("watchlist", "自选"),
    CUSTOM("custom", "自定义"),
    STRATEGY("strategy", "策略池"),
    SECTOR("sector", "行业板块");

    private final String code;
    private final String label;

    PoolType(String code, String label) {
        this.code = code;
        this.label = label;
    }

    public static PoolType fromCode(String code) {
        if (code == null) return CUSTOM;
        for (PoolType type : values()) {
            if (type.code.equalsIgnoreCase(code)) return type;
        }
        return CUSTOM;
    }
}
