package com.attribution.interfaces.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 统一响应封装
 *
 * <p>对应设计文档 docs/design/api/03-api-response.md §2.1
 *
 * <pre>
 * {
 *   "code": 0,           // 0 = 成功，!= 0 = 失败（见 ErrorCode）
 *   "data": { ... },
 *   "msg": "ok"
 * }
 * </pre>
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "统一响应封装")
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApiResponse<T> {

    @Schema(description = "业务状态码（0=成功，!=0=失败）")
    private int code;

    @Schema(description = "业务数据（成功时为具体内容，失败时为 null）")
    private T data;

    @Schema(description = "文案（成功为 ok，失败为可展示给用户的错误描述）")
    private String msg;

    // ── 静态工厂方法 ─────────────────────────────────────────

    public static <T> ApiResponse<T> ok(T data) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.SUCCESS.getCode())
                .data(data)
                .msg(ErrorCode.SUCCESS.getMsg())
                .build();
    }

    public static <T> ApiResponse<T> ok(T data, String msg) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.SUCCESS.getCode())
                .data(data)
                .msg(msg)
                .build();
    }

    public static <T> ApiResponse<T> error(ErrorCode errorCode) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .data(null)
                .msg(errorCode.getMsg())
                .build();
    }

    public static <T> ApiResponse<T> error(ErrorCode errorCode, String msg) {
        return ApiResponse.<T>builder()
                .code(errorCode.getCode())
                .data(null)
                .msg(msg)
                .build();
    }

    public static <T> ApiResponse<T> error(int code, String msg) {
        return ApiResponse.<T>builder()
                .code(code)
                .data(null)
                .msg(msg)
                .build();
    }

    public static <T> ApiResponse<T> created(T data) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.SUCCESS.getCode())
                .data(data)
                .msg("created")
                .build();
    }

    public static <T> ApiResponse<T> created(T data, String msg) {
        return ApiResponse.<T>builder()
                .code(ErrorCode.SUCCESS.getCode())
                .data(data)
                .msg(msg)
                .build();
    }
}
