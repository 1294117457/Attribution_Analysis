package com.attribution.auth.vo;

import lombok.Data;

/**
 * 登录令牌视图对象。
 *
 * <p>{@code userInfo} 仅登录接口返回，刷新接口不带。
 */
@Data
public class TokenVO {
    private String accessToken;
    private String refreshToken;
    private String tokenType = "Bearer";
    private Long expiresIn;
    private UserVO userInfo;
}
