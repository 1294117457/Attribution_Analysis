package com.attribution.auth.vo;

import lombok.Data;

/** 发送邮箱验证码结果 */
@Data
public class SendCodeVO {
    private Integer expireSeconds = 300;
    private String purpose;
}
