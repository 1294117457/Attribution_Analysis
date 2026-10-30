package com.attribution.auth.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.auth.service.AuthService;
import com.attribution.common.response.ApiResponse;

import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/permissions")
@RequiredArgsConstructor
public class PermissionController {
    private final AuthService authService;

    @GetMapping("/")
    public ApiResponse<?> all() {
        return ApiResponse.ok(authService.permissions());
    }
}
