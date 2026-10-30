package com.attribution.user.dto;

import jakarta.validation.constraints.Size;

import lombok.Data;

/** 更新池成员备注入参（单字段，保持轻量） */
@Data
public class PoolMemberMemoRequest {
    @Size(max = 255, message = "备注最长 255 字符")
    private String memo;
}
