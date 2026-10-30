package com.attribution.auth.dto;

import jakarta.validation.constraints.NotBlank;

import lombok.Data;

/** 刷新令牌入参 */
@Data
public class RefreshRequest {
    @NotBlank(message = "refresh token 不能为空")
    private String refreshToken;
}
