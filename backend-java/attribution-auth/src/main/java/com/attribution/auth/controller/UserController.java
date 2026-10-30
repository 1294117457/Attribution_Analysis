package com.attribution.auth.controller;

import java.util.Map;

import org.springframework.web.bind.annotation.*;

import com.attribution.auth.dto.AssignRoleRequest;
import com.attribution.auth.dto.ResetPasswordRequest;
import com.attribution.auth.dto.UpdateStatusRequest;
import com.attribution.auth.dto.UserQuery;
import com.attribution.auth.service.AuthService;
import com.attribution.common.response.ApiResponse;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {
    private final AuthService authService;

    @GetMapping("/")
    public ApiResponse<?> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int page_size,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Boolean is_active) {
        UserQuery query = new UserQuery();
        query.setPage(page);
        query.setPageSize(page_size);
        query.setKeyword(keyword);
        query.setIsActive(is_active);
        return ApiResponse.ok(authService.listUsers(query));
    }

    @PatchMapping("/{id}/status")
    public ApiResponse<?> updateStatus(
            @PathVariable int id, @Valid @RequestBody UpdateStatusRequest request) {
        return ApiResponse.ok(authService.setStatus(id, request));
    }

    @PostMapping("/{id}/reset-password")
    public ApiResponse<?> resetPassword(
            @PathVariable int id, @Valid @RequestBody ResetPasswordRequest request) {
        authService.resetPassword(id, request);
        return ApiResponse.ok(Map.of("message", "ok"));
    }

    @PostMapping("/{id}/roles")
    public ApiResponse<?> assignRole(
            @PathVariable int id, @Valid @RequestBody AssignRoleRequest request) {
        authService.assignRole(id, request);
        return ApiResponse.ok(Map.of("message", "ok"));
    }

    @DeleteMapping("/{id}/roles/{rid}")
    public ApiResponse<?> removeRole(@PathVariable int id, @PathVariable int rid) {
        authService.removeRole(id, rid);
        return ApiResponse.ok(Map.of("message", "ok"));
    }
}
