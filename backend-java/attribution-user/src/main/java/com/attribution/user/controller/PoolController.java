package com.attribution.user.controller;

import java.util.List;
import java.util.Map;

import org.springframework.web.bind.annotation.*;

import com.attribution.common.response.ApiResponse;
import com.attribution.user.dto.PoolCreateRequest;
import com.attribution.user.dto.PoolMemberMemoRequest;
import com.attribution.user.dto.PoolMembersRequest;
import com.attribution.user.dto.PoolOperationCreateRequest;
import com.attribution.user.dto.PoolQuery;
import com.attribution.user.dto.PoolUpdateRequest;
import com.attribution.user.service.PoolService;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class PoolController {
    private final PoolService poolService;

    @PostMapping("/pools")
    public ApiResponse<?> create(@Valid @RequestBody PoolCreateRequest request) {
        return ApiResponse.created(poolService.create(request));
    }

    @GetMapping("/pools")
    public ApiResponse<?> list(
            @RequestParam(defaultValue = "false") boolean include_archived,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int page_size) {
        PoolQuery query = new PoolQuery();
        query.setIncludeArchived(include_archived);
        query.setPage(page);
        query.setPageSize(page_size);
        return ApiResponse.ok(poolService.list(query));
    }

    @GetMapping("/pools/{id}")
    public ApiResponse<?> one(@PathVariable("id") int id) {
        return ApiResponse.ok(poolService.one(id));
    }

    @PatchMapping("/pools/{id}")
    public ApiResponse<?> patch(
            @PathVariable("id") int id, @Valid @RequestBody PoolUpdateRequest request) {
        return ApiResponse.ok(poolService.patch(id, request));
    }

    @DeleteMapping("/pools/{id}")
    public ApiResponse<?> delete(@PathVariable("id") int id) {
        poolService.delete(id);
        return ApiResponse.ok(Map.of("message", "删除成功"));
    }

    @PostMapping("/pools/{id}/members")
    public ApiResponse<?> addMembers(
            @PathVariable("id") int id, @Valid @RequestBody PoolMembersRequest request) {
        return ApiResponse.ok(poolService.addMembers(id, request));
    }

    @DeleteMapping("/pools/{id}/members")
    public ApiResponse<?> removeMembers(
            @PathVariable("id") int id, @Valid @RequestBody PoolMembersRequest request) {
        int removed = poolService.removeMembers(id, request);
        return ApiResponse.ok(Map.of("removed_count", removed));
    }

    @GetMapping("/pools/{id}/members")
    public ApiResponse<?> members(
            @PathVariable("id") int id,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "100") int page_size) {
        return ApiResponse.ok(poolService.members(id, Math.max(page, 1), Math.max(page_size, 1)));
    }

    @PatchMapping("/pools/{id}/members/{symbol}")
    public ApiResponse<?> memo(
            @PathVariable("id") int id,
            @PathVariable String symbol,
            @Valid @RequestBody PoolMemberMemoRequest request) {
        return ApiResponse.ok(poolService.memo(id, symbol, request));
    }

    @DeleteMapping("/pools/{id}/members/{symbol}")
    public ApiResponse<?> removeMember(@PathVariable("id") int id, @PathVariable String symbol) {
        PoolMembersRequest request = new PoolMembersRequest();
        request.setSymbols(List.of(symbol));
        poolService.removeMembers(id, request);
        return ApiResponse.ok(Map.of("message", "成员已移除"));
    }

    @GetMapping("/pools/by-symbol/{symbol}")
    public ApiResponse<?> bySymbol(@PathVariable String symbol) {
        return ApiResponse.ok(poolService.bySymbol(symbol));
    }

    @PostMapping("/pools/{id}/operations")
    public ApiResponse<?> createOperation(
            @PathVariable("id") int id, @Valid @RequestBody PoolOperationCreateRequest request) {
        return ApiResponse.created(poolService.createOp(id, request));
    }

    @GetMapping("/pools/{id}/operations")
    public ApiResponse<?> operations(
            @PathVariable("id") int id,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int page_size) {
        return ApiResponse.ok(poolService.ops(id, Math.max(page, 1), Math.max(page_size, 1)));
    }

    @GetMapping("/operations/{op_id}")
    public ApiResponse<?> operation(@PathVariable("op_id") int id) {
        return ApiResponse.ok(poolService.opOne(id));
    }

    @GetMapping("/operations/{op_id}/progress")
    public ApiResponse<?> operationProgress(@PathVariable("op_id") int id) {
        return ApiResponse.ok(poolService.opProgress(id));
    }

    @PostMapping("/operations/{op_id}/cancel")
    public ApiResponse<?> cancelOperation(@PathVariable("op_id") int id) {
        poolService.cancel(id);
        return ApiResponse.ok(Map.of("message", "操作已取消"));
    }
}
