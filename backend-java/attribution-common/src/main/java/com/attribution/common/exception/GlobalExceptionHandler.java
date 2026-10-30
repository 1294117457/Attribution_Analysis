package com.attribution.common.exception;

import java.util.stream.Collectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;

/**
 * 全局异常处理器：把异常统一映射成 HTTP 响应。
 *
 * <p>规范见 {@code docs/规范文档/横切技术规范/异常与响应规范.md}。
 *
 * <p>核心约定：
 * <ul>
 *   <li>响应体永远是 {@code {code, message, data}}，前端拦截器零改动</li>
 *   <li>异常细节只进日志，**不进响应 message**（避免泄漏 SQL / 表名 / 内部路径）</li>
 *   <li>未预期异常统一返回通用文案，原始 message 只写日志</li>
 * </ul>
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** 业务异常：由 Service 层主动抛出，code 即 HTTP 状态码 */
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResponse<?>> business(BusinessException ex) {
        // 业务异常是「预期内」的失败，只记 warn 且不打堆栈，避免污染日志
        log.warn("业务异常 code={} message={}", ex.getCode(), ex.getMessage());
        return ResponseEntity.status(ex.getCode()).body(ApiResponse.fail(ex.getCode(), ex.getMessage()));
    }

    /** 参数校验失败：收集全部字段错误，一次性返回，避免用户逐个试错 */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<?>> validation(MethodArgumentNotValidException ex) {
        String message =
                ex.getBindingResult().getFieldErrors().stream()
                        .map(error -> error.getField() + ": " + error.getDefaultMessage())
                        .collect(Collectors.joining("; "));
        if (message.isBlank()) message = "请求参数校验失败";
        log.warn("参数校验失败: {}", message);
        return ResponseEntity.status(422).body(ApiResponse.fail(422, message));
    }

    /**
     * 兜底：未预期异常。
     *
     * <p>⚠️ 响应里**只返回通用文案**——原始 {@code ex.getMessage()} 可能包含 SQL 语句、
     * 表名、字段名、内部路径，属于信息泄漏。原始异常与堆栈完整写入日志。
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<?>> unexpected(Exception ex) {
        log.error("未预期异常", ex);
        return ResponseEntity.status(500).body(ApiResponse.fail(500, "服务器内部错误，请稍后重试"));
    }
}
