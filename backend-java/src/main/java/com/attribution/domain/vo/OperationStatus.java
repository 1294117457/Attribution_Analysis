package com.attribution.domain.vo;

import lombok.Getter;

@Getter
public enum OperationStatus {

    PENDING("pending"),
    RUNNING("running"),
    COMPLETED("completed"),
    FAILED("failed"),
    CANCELLED("cancelled"),
    SKIPPED("skipped");

    private final String code;

    OperationStatus(String code) {
        this.code = code;
    }

    public static OperationStatus fromCode(String code) {
        if (code == null) return PENDING;
        for (OperationStatus s : values()) {
            if (s.code.equalsIgnoreCase(code)) return s;
        }
        return PENDING;
    }

    public boolean isTerminal() {
        return this == COMPLETED || this == FAILED || this == CANCELLED || this == SKIPPED;
    }
}
