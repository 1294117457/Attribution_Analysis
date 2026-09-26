package com.attribution.application.service;

import com.attribution.application.service.collect.BaseCollectTask;
import com.attribution.application.service.collect.CollectTaskProgress;
import com.attribution.application.service.collect.KlineCollectTask;
import com.attribution.application.service.collect.DailyBasicCollectTask;
import com.attribution.application.service.collect.FinReportCollectTask;
import com.attribution.application.service.collect.ConceptCollectTask;
import com.attribution.domain.entity.SysCollectTaskEntity;
import com.attribution.domain.repository.SysCollectTaskRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 采集任务服务 - 路由到具体的 Task
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CollectTaskService {

    private final KlineCollectTask klineCollectTask;
    private final DailyBasicCollectTask dailyBasicCollectTask;
    private final FinReportCollectTask finReportCollectTask;
    private final ConceptCollectTask conceptCollectTask;
    private final SysCollectTaskRepository taskRepository;

    private static final Map<String, BaseCollectTask<?>> TASK_MAP = new ConcurrentHashMap<>();

    public Long triggerTask(String taskType, Map<String, Object> params, String triggerType) {
        BaseCollectTask<?> task = resolveTask(taskType);
        if (task == null) {
            throw new com.attribution.infrastructure.exception.BusinessException(
                "collect", "INVALID_TASK_TYPE", "未知任务类型: " + taskType, 400);
        }
        log.info("触发采集任务: type={}, trigger={}", taskType, triggerType);
        return task.executeAsync(params, triggerType);
    }

    public CollectTaskProgress getProgress(Long taskId, String taskType) {
        BaseCollectTask<?> task = resolveTask(taskType);
        return task != null ? task.getProgress(taskId) : null;
    }

    public Page<SysCollectTaskEntity> listTasks(String taskType, String status, Pageable pageable) {
        boolean hasType = taskType != null && !taskType.isBlank();
        boolean hasStatus = status != null && !status.isBlank();
        if (hasType && hasStatus) {
            return taskRepository.findByTaskTypeAndStatusOrderByIdDesc(taskType, status, pageable);
        }
        if (hasType) {
            return taskRepository.findByTaskTypeOrderByIdDesc(taskType, pageable);
        }
        if (hasStatus) {
            return taskRepository.findByStatusOrderByIdDesc(status, pageable);
        }
        return taskRepository.findAllByOrderByIdDesc(pageable);
    }

    public SysCollectTaskEntity getTask(Long taskId) {
        return taskRepository.findById(taskId).orElse(null);
    }

    @Transactional
    public boolean cancelTask(Long taskId, boolean force) {
        SysCollectTaskEntity task = taskRepository.findById(taskId).orElse(null);
        if (task == null) {
            return false;
        }
        String status = task.getStatus();
        if ("success".equals(status) || "failed".equals(status) || "cancelled".equals(status)) {
            if (!force) {
                return false;
            }
        }
        task.setStatus("cancelled");
        task.setFinishedAt(LocalDateTime.now());
        if (task.getStartedAt() != null) {
            task.setDurationMs((int) java.time.Duration.between(task.getStartedAt(), task.getFinishedAt()).toMillis());
        }
        task.setMessage(force ? "强制取消" : "已取消");
        taskRepository.save(task);
        return true;
    }

    private BaseCollectTask<?> resolveTask(String taskType) {
        return switch (taskType) {
            case "kline_daily" -> klineCollectTask;
            case "daily_basic" -> dailyBasicCollectTask;
            case "fin_report" -> finReportCollectTask;
            case "concept_sync" -> conceptCollectTask;
            default -> null;
        };
    }
}
