package com.attribution.common.response;

import lombok.Data;

@Data
public class ApiResponse<T> {
    private int code;
    private String message;
    private T data;

    public static <T> ApiResponse<T> ok(T data) {
        ApiResponse<T> resp = new ApiResponse<>();
        resp.code = 200;
        resp.message = "success";
        resp.data = data;
        return resp;
    }

    public static <T> ApiResponse<T> ok() {
        return ok(null);
    }

    public static <T> ApiResponse<T> created(T data) {
        ApiResponse<T> resp = new ApiResponse<>();
        resp.code = 201;
        resp.message = "创建成功";
        resp.data = data;
        return resp;
    }

    public static <T> ApiResponse<T> fail(int code, String message) {
        ApiResponse<T> resp = new ApiResponse<>();
        resp.code = code;
        resp.message = message;
        return resp;
    }
}
