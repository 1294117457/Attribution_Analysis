package com.attribution.interfaces.controller;

import com.attribution.interfaces.dto.operation.PoolKlineCollectRequest;
import com.attribution.interfaces.dto.operation.PoolOperationCreateVO;
import com.attribution.interfaces.dto.operation.PoolOperationListRequest;
import com.attribution.interfaces.dto.operation.PoolOperationListVO;
import com.attribution.interfaces.dto.operation.PoolOperationProgressVO;
import com.attribution.interfaces.dto.operation.PoolOperationVO;
import com.attribution.interfaces.dto.pool.PoolAddMembersRequest;
import com.attribution.interfaces.dto.pool.PoolAddMembersVO;
import com.attribution.interfaces.dto.pool.PoolCreateRequest;
import com.attribution.interfaces.dto.pool.PoolDetailVO;
import com.attribution.interfaces.dto.pool.PoolListVO;
import com.attribution.interfaces.dto.pool.PoolMemberListVO;
import com.attribution.interfaces.dto.pool.PoolMemberVO;
import com.attribution.interfaces.dto.pool.PoolPoolsBySymbolVO;
import com.attribution.interfaces.dto.pool.PoolRemoveMembersRequest;
import com.attribution.interfaces.dto.pool.PoolUpdateMemberMemoRequest;
import com.attribution.interfaces.dto.pool.PoolUpdateRequest;
import com.attribution.interfaces.dto.pool.PoolVO;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.application.service.PoolOperationService;
import com.attribution.application.service.StockPoolService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1")
@RequiredArgsConstructor
@Tag(name = "操作", description = "用户操作_CRUD 与成员管")
public class PoolController {

    private final StockPoolService poolService;
    private final PoolOperationService operationService;

    // ── _CRUD ─────────────────────────────────────────────────────────

    @PostMapping("/pools")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "创建")
    public ResponseEntity<ApiResponse<PoolVO>> createPool(@Valid @RequestBody PoolCreateRequest request) {
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(ApiResponse.created(poolService.createPool(request), "创建成功"));
    }

    @GetMapping("/pools")
    @Operation(summary = "池列")
    public ResponseEntity<ApiResponse<PoolListVO>> listPools(
            @RequestParam(defaultValue = "false") Boolean includeArchived,
            @RequestParam(defaultValue = "100") @Min(1) @Max(500) Integer limit,
            @RequestParam(defaultValue = "0") @Min(0) Integer offset) {
        return ResponseEntity.ok(ApiResponse.ok(
            poolService.listPools(includeArchived, limit, offset)));
    }

    @GetMapping("/pools/{poolId}")
    @Operation(summary = "池详")
    public ResponseEntity<ApiResponse<PoolDetailVO>> getPool(@PathVariable Long poolId) {
        return ResponseEntity.ok(ApiResponse.ok(poolService.getPool(poolId)));
    }

    @PatchMapping("/pools/{poolId}")
    @Operation(summary = "更新")
    public ResponseEntity<ApiResponse<PoolVO>> updatePool(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolUpdateRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(
            poolService.updatePool(poolId, request), "更新成功"));
    }

    @DeleteMapping("/pools/{poolId}")
    @Operation(summary = "删除")
    public ResponseEntity<ApiResponse<Void>> deletePool(@PathVariable Long poolId) {
        poolService.deletePool(poolId);
        return ResponseEntity.ok(ApiResponse.ok(null, "删除成功"));
    }

    // ── 成员管理 ───────────────────────────────────────────────────────

    @PostMapping("/pools/{poolId}/members")
    @Operation(summary = "批量添加成员")
    public ResponseEntity<ApiResponse<PoolAddMembersVO>> addMembers(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolAddMembersRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(
            poolService.addMembers(poolId, request), "添加完成"));
    }

    @DeleteMapping("/pools/{poolId}/members")
    @Operation(summary = "批量删除成员")
    public ResponseEntity<ApiResponse<Map<String, Object>>> removeMembers(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolRemoveMembersRequest request) {
        int count = poolService.removeMembers(poolId, request);
        return ResponseEntity.ok(ApiResponse.ok(
            Map.of("removed_count", count),
            "成功移除 " + count + " 个成"));
    }

    @GetMapping("/pools/{poolId}/members")
    @Operation(summary = "成员列表")
    public ResponseEntity<ApiResponse<PoolMemberListVO>> listMembers(
            @PathVariable Long poolId,
            @RequestParam(defaultValue = "100") @Min(1) @Max(1000) Integer limit,
            @RequestParam(defaultValue = "0") @Min(0) Integer offset) {
        return ResponseEntity.ok(ApiResponse.ok(
            poolService.listMembers(poolId, limit, offset)));
    }

    @PatchMapping("/pools/{poolId}/members/{symbol}")
    @Operation(summary = "更新成员备注")
    public ResponseEntity<ApiResponse<PoolMemberVO>> updateMemberMemo(
            @PathVariable Long poolId,
            @PathVariable String symbol,
            @Valid @RequestBody PoolUpdateMemberMemoRequest request) {
        request.setSymbol(symbol);
        return ResponseEntity.ok(ApiResponse.ok(
            poolService.updateMemberMemo(poolId, request), "更新成功"));
    }

    @DeleteMapping("/pools/{poolId}/members/{symbol}")
    @Operation(summary = "删除单个成员")
    public ResponseEntity<ApiResponse<Void>> removeMember(
            @PathVariable Long poolId,
            @PathVariable String symbol) {
        poolService.removeMembers(poolId, PoolRemoveMembersRequest.builder()
            .symbols(java.util.List.of(symbol))
            .build());
        return ResponseEntity.ok(ApiResponse.ok(null, "成员已移"));
    }

    // ── 反向查询 ───────────────────────────────────────────────────────

    @GetMapping("/pools/by-symbol/{symbol}")
    @Operation(summary = "股票在哪些池")
    public ResponseEntity<ApiResponse<PoolPoolsBySymbolVO>> findPoolsBySymbol(
            @PathVariable String symbol) {
        return ResponseEntity.ok(ApiResponse.ok(
            poolService.findPoolsBySymbol(symbol)));
    }

    // ── 池操_─────────────────────────────────────────────────────────

    @PostMapping("/pools/{poolId}/operations")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "发起池操")
    public ResponseEntity<ApiResponse<PoolOperationCreateVO>> createOperation(
            @PathVariable Long poolId,
            @Valid @RequestBody PoolKlineCollectRequest request) {
        request.setPoolId(poolId);
        PoolOperationCreateVO result = operationService.createKlineCollectOperation(request);
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(ApiResponse.created(result, result.getMessage()));
    }

    @GetMapping("/pools/{poolId}/operations")
    @Operation(summary = "操作历史")
    public ResponseEntity<ApiResponse<PoolOperationListVO>> listOperations(
            @PathVariable Long poolId,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) Integer limit,
            @RequestParam(defaultValue = "0") @Min(0) Integer offset) {
        return ResponseEntity.ok(ApiResponse.ok(
            operationService.listOperations(PoolOperationListRequest.builder()
                .poolId(poolId)
                .limit(limit)
                .offset(offset)
                .build())));
    }
}
