package com.attribution.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import lombok.Data;

/** 登录入参：邮箱 + 密码 + 图形验证码 */
@Data
public class LoginRequest {
    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 64, message = "密码长度需在 6-64 位之间")
    private String password;

    @NotBlank(message = "图形验证码不能为空")
    private String captchaId;

    @NotBlank(message = "验证码不能为空")
    private String captchaCode;

    /** user-agent 由后端从 HttpServletRequest 取，不接受前端传 */
    private String userAgent;

    /** 客户端 IP 同上 */
    private String clientIp;
}
