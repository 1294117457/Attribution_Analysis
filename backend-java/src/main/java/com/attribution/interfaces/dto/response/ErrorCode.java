package com.attribution.interfaces.dto.response;

import lombok.AllArgsConstructor;
import lombok.Getter;

/**
 * 业务错误码枚举（对应设计文档 docs/design/api/03-api-response.md §3.2）
 *
 * <ul>
 *   <li>0      = 业务成功</li>
 *   <li>1xxxx  = 客户端错误（HTTP 4xx 同步）</li>
 *   <li>2xxxx  = 业务错误（通常 HTTP 200）</li>
 *   <li>3xxxx  = 第三方 / 外部错误（HTTP 502）</li>
 *   <li>5xxxx  = 服务端内部错误（HTTP 500）</li>
 * </ul>
 */
@Getter
@AllArgsConstructor
public enum ErrorCode {

    SUCCESS(0, "ok"),

    // ========== 客户端错误 1xxxx ==========
    BAD_REQUEST(10001, "请求参数错误"),
    MISSING_PARAM(10002, "缺少必要参数"),
    INVALID_PARAM(10003, "参数值非法"),
    UNAUTHORIZED(11001, "未登录或登录已过期"),
    FORBIDDEN(11002, "无权限访问"),
    NOT_FOUND(12001, "资源不存在"),

    // ========== 业务错误 2xxxx ==========
    STOCK_NOT_FOUND(20001, "股票不存在"),
    POOL_NOT_FOUND(20101, "股票池不存在"),
    POOL_MEMBER_EXISTS(20102, "成员已存在"),
    POOL_MEMBER_NOT_FOUND(20103, "成员不存在"),
    CONCEPT_NOT_FOUND(20201, "概念不存在"),
    KLINE_NOT_FOUND(20301, "K 线不存在"),
    TASK_NOT_FOUND(20401, "任务不存在"),
    TASK_ALREADY_RUNNING(20402, "任务正在运行"),
    TASK_ALREADY_CANCELED(20403, "任务已取消"),

    // ========== 第三方 / 外部错误 3xxxx ==========
    TUSHARE_API_ERROR(30001, "Tushare 接口调用失败"),
    PYTDX_API_ERROR(30002, "Pytdx 接口调用失败"),
    AKSHARE_API_ERROR(30003, "AkShare 接口调用失败"),
    EAST_MONEY_API_ERROR(30004, "东方财富接口调用失败"),

    // ========== 服务端错误 5xxxx ==========
    INTERNAL_ERROR(50001, "服务内部异常"),
    DB_ERROR(50002, "数据库异常"),
    CACHE_ERROR(50003, "缓存异常"),
    REMOTE_CALL_ERROR(50004, "下游服务调用失败");

    private final int code;
    private final String msg;
}
