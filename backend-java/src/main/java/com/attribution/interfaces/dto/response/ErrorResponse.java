package com.attribution.interfaces.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ErrorResponse {

    private int code;
    private String message;
    private Object data;

    public static ErrorResponse of(int code, String message) {
        return ErrorResponse.builder()
                .code(code)
                .message(message)
                .data(null)
                .build();
    }

    public static ErrorResponse of(int code, String message, Object data) {
        return ErrorResponse.builder()
                .code(code)
                .message(message)
                .data(data)
                .build();
    }

    /**
     * 业务错误响应：HTTP 状态码_body.code 分别赋值（用于鉴权 / 限流_特殊解_场景）_     *
     * <ul>
     *   <li>{@code code}     _HTTP 状态码（如 401 / 403 / 429_/li>
     *   <li>{@code message}  _业务错误码字符串（如 "TOKEN_EXPIRED"_/li>
     *   <li>{@code data}     _人话消息（如 "token 已过期，请重新登__/li>
     * </ul>
     */
    public static ErrorResponse ofBiz(int httpStatus, String bizCode, String humanMessage) {
        return ErrorResponse.builder()
                .code(httpStatus)
                .message(bizCode)
                .data(humanMessage)
                .build();
    }
}
