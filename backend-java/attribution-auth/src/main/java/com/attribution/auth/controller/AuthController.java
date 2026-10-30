package com.attribution.auth.controller;

import org.springframework.web.bind.annotation.*;

import com.attribution.auth.dto.ChangePasswordRequest;
import com.attribution.auth.dto.ForgotResetRequest;
import com.attribution.auth.dto.LoginRequest;
import com.attribution.auth.dto.RegisterRequest;
import com.attribution.auth.dto.RefreshRequest;
import com.attribution.auth.dto.SendCodeRequest;
import com.attribution.auth.service.AuthService;
import com.attribution.common.response.ApiResponse;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {
    private final AuthService authService;

    @PostMapping("/login")
    public ApiResponse<?> login(
            @Valid @RequestBody LoginRequest request, HttpServletRequest httpRequest) {
        request.setUserAgent(httpRequest.getHeader("user-agent"));
        request.setClientIp(httpRequest.getRemoteAddr());
        return ApiResponse.ok(authService.login(request));
    }

    @PostMapping("/refresh")
    public ApiResponse<?> refresh(@Valid @RequestBody RefreshRequest request) {
        return ApiResponse.ok(authService.refresh(request.getRefreshToken()));
    }

    @PostMapping("/logout")
    public ApiResponse<?> logout(@RequestHeader(value = "Authorization", required = false) String auth) {
        authService.logout(auth);
        return ApiResponse.ok(java.util.Map.of("message", "已登出"));
    }

    @GetMapping("/me")
    public ApiResponse<?> me(@RequestHeader(value = "Authorization", required = false) String auth) {
        return ApiResponse.ok(authService.me(auth));
    }

    @GetMapping("/captcha/generate")
    public ApiResponse<?> captcha() {
        return ApiResponse.ok(authService.captcha());
    }

    @PostMapping("/register")
    public ApiResponse<?> register(@Valid @RequestBody RegisterRequest request) {
        return ApiResponse.created(authService.register(request));
    }

    @PostMapping("/send-verification-code")
    public ApiResponse<?> sendVerificationCode(@Valid @RequestBody SendCodeRequest request) {
        return ApiResponse.ok(authService.sendCode(request));
    }

    @PostMapping("/change-password")
    public ApiResponse<?> changePassword(
            @RequestHeader(value = "Authorization", required = false) String auth,
            @Valid @RequestBody ChangePasswordRequest request) {
        authService.changePassword(auth, request);
        return ApiResponse.ok(java.util.Map.of("message", "ok"));
    }

    @PostMapping("/forgot-password/send-code")
    public ApiResponse<?> forgotPasswordSendCode(@Valid @RequestBody SendCodeRequest request) {
        request.setPurpose("reset_password");
        return ApiResponse.ok(authService.sendCode(request));
    }

    @PostMapping("/forgot-password/reset")
    public ApiResponse<?> forgotPasswordReset(@Valid @RequestBody ForgotResetRequest request) {
        authService.forgotReset(request);
        return ApiResponse.ok(java.util.Map.of("message", "ok"));
    }
}
