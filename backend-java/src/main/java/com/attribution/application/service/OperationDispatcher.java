package com.attribution.application.service;

import com.attribution.domain.entity.PoolOperationEntity;
import com.attribution.domain.repository.PoolOperationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

@Component
@RequiredArgsConstructor
@Slf4j
public class OperationDispatcher {

    private final PoolOperationRepository operationRepository;
    private final KlineCollectionExecutor executor;

    private final ExecutorService virtualThreadPool = Executors.newVirtualThreadPerTaskExecutor();
    private final Map<Long, CompletableFuture<?>> runningTasks = new ConcurrentHashMap<>();

    public void dispatchKlineCollect(Long opId, Long poolId, List<String> symbols, int days) {
        CompletableFuture<?> task = CompletableFuture.runAsync(() -> {
            try {
                runCollect(opId, symbols, days);
            } catch (Exception e) {
                log.error("采集任务执行失败: opId={}", opId, e);
                markFailed(opId, e.getMessage());
            }
        }, virtualThreadPool);
        runningTasks.put(opId, task);
    }

    private void runCollect(Long opId, List<String> symbols, int days) {
        markRunning(opId, symbols.size());

        AtomicInteger done = new AtomicInteger(0);
        AtomicInteger failed = new AtomicInteger(0);
        StringBuilder errors = new StringBuilder();

        for (String symbol : symbols) {
            try {
                executor.collectOne(symbol, days);
            } catch (Exception e) {
                log.warn("采集失败: {}", symbol, e);
                failed.incrementAndGet();
                if (errors.length() > 0) errors.append("\n");
                errors.append(symbol).append(": ").append(e.getMessage());
            }
            int current = done.incrementAndGet();
            updateProgress(opId, current, symbols.size(), failed.get());
        }

        markCompleted(opId, symbols.size(), failed.get(), errors.toString());
    }

    public void cancel(Long opId) {
        CompletableFuture<?> task = runningTasks.remove(opId);
        if (task != null && !task.isDone()) {
            task.cancel(true);
        }
    }

    @Transactional
    protected void markRunning(Long opId, int total) {
        operationRepository.findById(opId).ifPresent(op -> {
            op.setStatus("running");
            op.setStartedAt(LocalDateTime.now());
            op.setProgress(Map.of("done", 0, "total", total, "failed", 0));
            operationRepository.save(op);
        });
    }

    @Transactional
    protected void updateProgress(Long opId, int done, int total, int failed) {
        operationRepository.findById(opId).ifPresent(op -> {
            op.setProgress(Map.of("done", done, "total", total, "failed", failed));
            operationRepository.save(op);
        });
    }

    @Transactional
    protected void markCompleted(Long opId, int total, int failed, String errorMessage) {
        operationRepository.findById(opId).ifPresent(op -> {
            op.setStatus(failed == total ? "failed" : "completed");
            op.setFinishedAt(LocalDateTime.now());
            op.setProgress(Map.of("done", total, "total", total, "failed", failed));
            if (errorMessage != null && !errorMessage.isEmpty()) {
                op.setErrorMessage(errorMessage);
            }
            Map<String, Object> summary = new HashMap<>();
            summary.put("total", total);
            summary.put("succeeded", total - failed);
            summary.put("failed", failed);
            op.setResultSummary(summary);
            operationRepository.save(op);
        });
        runningTasks.remove(opId);
    }

    @Transactional
    protected void markFailed(Long opId, String errorMessage) {
        operationRepository.findById(opId).ifPresent(op -> {
            op.setStatus("failed");
            op.setFinishedAt(LocalDateTime.now());
            op.setErrorMessage(errorMessage);
            operationRepository.save(op);
        });
        runningTasks.remove(opId);
    }
}
