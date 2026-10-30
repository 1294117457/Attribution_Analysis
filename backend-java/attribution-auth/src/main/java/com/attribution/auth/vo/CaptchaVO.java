package com.attribution.auth.vo;

import lombok.Data;

/** 图形验证码视图对象 */
@Data
public class CaptchaVO {
    private String captchaId;
    private String base64;
}
