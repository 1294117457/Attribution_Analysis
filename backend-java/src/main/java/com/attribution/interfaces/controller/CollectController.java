package com.attribution.interfaces.controller;

import com.attribution.interfaces.dto.CollectTaskProgressVO;
import com.attribution.interfaces.dto.CollectTaskRequest;
import com.attribution.interfaces.dto.response.ApiResponse;
import com.attribution.infrastructure.exception.BusinessException;
import com.attribution.application.service.CollectTaskService;
import com.attribution.domain.entity.SysCollectTaskEntity;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 采集任务管理 - 与前端 api.ts 对齐：
 *   POST   /collect/tasks
 *   GET    /collect/tasks
 *   GET    /collect/tasks/{taskId}
 *   GET    /collect/tasks/{taskId}/progress
 *   POST   /collect/tasks/{taskId}/cancel
 */
@RestController
@RequestMapping("/api/v1/collect/tasks")
@RequiredArgsConstructor
@Tag(name = "采集任务", description = "数据采集任务管理")
public class CollectController {

    private final CollectTaskService collectTaskService;

    @PostMapping
    @Operation(summary = "触发采集任务")
    public ResponseEntity<ApiResponse<Long>> triggerTask(@RequestBody CollectTaskRequest request) {
        Long taskId = collectTaskService.triggerTask(
            request.getTaskType(),
            request.toParams(),
            "manual"
        );
        return ResponseEntity.ok(ApiResponse.ok(taskId, "任务已触发"));
    }

    @GetMapping
    @Operation(summary = "任务列表")
    public ResponseEntity<ApiResponse<Map<String, Object>>> listTasks(
            @RequestParam(required = false) String taskType,
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int pageSize) {

        Page<SysCollectTaskEntity> result = collectTaskService.listTasks(
            taskType, status, PageRequest.of(Math.max(0, page - 1), Math.min(pageSize, 500)));

        List<Map<String, Object>> items = result.getContent().stream()
                .map(this::toVo)
                .collect(Collectors.toList());

        Map<String, Object> data = new java.util.LinkedHashMap<>();
        data.put("total", result.getTotalElements());
        data.put("page", page);
        data.put("pageSize", pageSize);
        data.put("dataList", items);
        return ResponseEntity.ok(ApiResponse.ok(data));
    }

    @GetMapping("/{taskId}")
    @Operation(summary = "任务详情")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getTask(@PathVariable Long taskId) {
        SysCollectTaskEntity task = collectTaskService.getTask(taskId);
        if (task == null) {
            throw new BusinessException("collect", "TASK_NOT_FOUND",
                    "任务不存在: " + taskId, 404);
        }
        return ResponseEntity.ok(ApiResponse.ok(toVo(task)));
    }

    @GetMapping("/{taskId}/progress")
    @Operation(summary = "查询任务进度")
    public ResponseEntity<ApiResponse<CollectTaskProgressVO>> getProgress(
            @PathVariable Long taskId,
            @RequestParam(defaultValue = "kline_daily") String taskType) {
        var progress = collectTaskService.getProgress(taskId, taskType);
        if (progress == null) {
            throw new BusinessException("collect", "TASK_NOT_FOUND",
                    "任务不存在: " + taskId, 404);
        }
        CollectTaskProgressVO vo = CollectTaskProgressVO.builder()
            .taskId(progress.getTaskId())
            .taskType(progress.getTaskType())
            .status(progress.getStatus())
            .total(progress.getTotal())
            .success(progress.getSuccess())
            .fail(progress.getFail())
            .skip(progress.getSkip())
            .progress(progress.getProgress())
            .message(progress.getMessage())
            .startedAt(progress.getStartedAt() != null ? progress.getStartedAt().toString() : null)
            .finishedAt(progress.getFinishedAt() != null ? progress.getFinishedAt().toString() : null)
            .durationMs(progress.getDurationMs())
            .build();
        return ResponseEntity.ok(ApiResponse.ok(vo));
    }

    @PostMapping("/{taskId}/cancel")
    @Operation(summary = "取消任务")
    public ResponseEntity<ApiResponse<Map<String, Object>>> cancelTask(
            @PathVariable Long taskId,
            @RequestParam(defaultValue = "false") boolean force) {
        boolean ok = collectTaskService.cancelTask(taskId, force);
        if (!ok) {
            throw new BusinessException("collect", "TASK_NOT_FOUND",
                    "任务不存在或无法取消: " + taskId, 404);
        }
        return ResponseEntity.ok(ApiResponse.ok(
                Map.of("id", taskId, "status", "cancelled"), "已取消"));
    }

    private Map<String, Object> toVo(SysCollectTaskEntity t) {
        Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("id", t.getId());
        m.put("task_type", t.getTaskType());
        m.put("trigger_type", t.getTriggerType());
        m.put("params", t.getParams());
        m.put("status", t.getStatus());
        m.put("total_count", t.getTotalCount());
        m.put("success_count", t.getSuccessCount());
        m.put("fail_count", t.getFailCount());
        m.put("skip_count", t.getSkipCount());
        m.put("started_at", t.getStartedAt() != null ? t.getStartedAt().toString() : null);
        m.put("finished_at", t.getFinishedAt() != null ? t.getFinishedAt().toString() : null);
        m.put("duration_ms", t.getDurationMs());
        m.put("message", t.getMessage());
        m.put("created_at", t.getCreatedAt() != null ? t.getCreatedAt().toString() : null);
        return m;
    }
}
