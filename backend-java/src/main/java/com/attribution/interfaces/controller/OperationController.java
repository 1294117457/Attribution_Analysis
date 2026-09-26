package com.attribution.interfaces.controller;

import com.attribution.interfaces.dto.operation.PoolOperationProgressVO;
import com.attribution.interfaces.dto.operation.PoolOperationVO;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.application.service.PoolOperationService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/operations")
@RequiredArgsConstructor
@Tag(name = "操作记录", description = "池操作详情与进度查询")
public class OperationController {

    private final PoolOperationService operationService;

    @GetMapping("/{opId}")
    @Operation(summary = "操作详情")
    public ResponseEntity<ApiResponse<PoolOperationVO>> getOperation(@PathVariable Long opId) {
        return ResponseEntity.ok(ApiResponse.ok(operationService.getOperation(opId)));
    }

    @GetMapping("/{opId}/progress")
    @Operation(summary = "操作进度（轻量）")
    public ResponseEntity<ApiResponse<PoolOperationProgressVO>> getProgress(@PathVariable Long opId) {
        return ResponseEntity.ok(ApiResponse.ok(operationService.getOperationProgress(opId)));
    }

    @PostMapping("/{opId}/cancel")
    @Operation(summary = "取消操作")
    public ResponseEntity<ApiResponse<PoolOperationVO>> cancel(@PathVariable Long opId) {
        return ResponseEntity.ok(ApiResponse.ok(
            operationService.cancelOperation(opId), "操作已取"));
    }
}
