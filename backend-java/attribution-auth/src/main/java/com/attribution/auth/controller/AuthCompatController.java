package com.attribution.auth.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.auth.dto.RefreshRequest;
import com.attribution.auth.service.AuthService;
import com.attribution.common.response.ApiResponse;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

/** 兼容别名：前端 http.ts 直调 /api/v1/auth/refresh，这里与 /api/auth 平行暴露。 */
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthCompatController {
    private final AuthService authService;

    @PostMapping("/refresh")
    public ApiResponse<?> refresh(@Valid @RequestBody RefreshRequest request) {
        return ApiResponse.ok(authService.refresh(request.getRefreshToken()));
    }

    @GetMapping("/me")
    public ApiResponse<?> me(@RequestHeader(value = "Authorization", required = false) String auth) {
        return ApiResponse.ok(authService.me(auth));
    }
}
