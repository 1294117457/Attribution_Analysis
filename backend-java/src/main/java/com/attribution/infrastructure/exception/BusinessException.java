package com.attribution.infrastructure.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * 通用业务异常_ *
 * <p>所有业务异常都通过本类抛出，由 {@code GlobalExceptionHandler} 统一映射_HTTP 响应_/p>
 *
 * <p>字段含义_ * <ul>
 *   <li>{@code module}     _业务模块，例_stock / pool / kline / concept / collect / operation</li>
 *   <li>{@code code}       _业务错误码，例如 STOCK_NOT_FOUND / POOL_DUPLICATE</li>
 *   <li>{@code httpStatus} _HTTP 状态码</li>
 *   <li>父类 message       _人话消息（不含方括号，便于前端展示）</li>
 * </ul>
 *
 * <p>用法_ * <pre>
 * throw new BusinessException("stock", "STOCK_NOT_FOUND", "股票不存_ " + symbol, 404);
 * throw new BusinessException("pool", "POOL_DUPLICATE", "股票池已存在同名股票");
 * </pre>
 */
@Getter
public class BusinessException extends RuntimeException {

    private final String module;

    private final String code;

    private final int httpStatus;

    public BusinessException(String module, String code, String message) {
        this(module, code, message, HttpStatus.BAD_REQUEST.value());
    }

    public BusinessException(String module, String code, String message, HttpStatus httpStatus) {
        this(module, code, message, httpStatus.value());
    }

    public BusinessException(String module, String code, String message, int httpStatus) {
        super(message);
        this.module = module == null ? "unknown" : module;
        this.code = code == null ? "UNDEFINED" : code;
        this.httpStatus = httpStatus;
    }
}
