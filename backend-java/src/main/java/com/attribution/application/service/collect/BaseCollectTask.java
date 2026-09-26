package com.attribution.application.service.collect;

import com.attribution.domain.entity.SysCollectTaskEntity;
import com.attribution.domain.entity.SysCollectTaskDetailEntity;
import com.attribution.domain.repository.SysCollectTaskDetailRepository;
import com.attribution.domain.repository.SysCollectTaskRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 采集任务基类 - 模板模式_ * 提供：任务持久化、实时进度存_Redis)、统计、异步执行框架_ *
 * @param <S> 待处理条目类_如股票代_String)
 */
@Slf4j
public abstract class BaseCollectTask<S> {

    private final SysCollectTaskRepository taskRepository;
    private final SysCollectTaskDetailRepository detailRepository;
    private final StringRedisTemplate redisTemplate;

    protected static final String PROGRESS_KEY_PREFIX = "collect:progress:";
    protected static final Duration PROGRESS_TTL = Duration.ofHours(24);

    protected BaseCollectTask(SysCollectTaskRepository taskRepository,
                             SysCollectTaskDetailRepository detailRepository,
                             StringRedisTemplate redisTemplate) {
        this.taskRepository = taskRepository;
        this.detailRepository = detailRepository;
        this.redisTemplate = redisTemplate;
    }

    /** 子类实现：任务类型标_*/
    protected abstract String taskType();

    /** 子类实现：待采集条目列表 */
    protected abstract S[] resolveItems(Map<String, Object> params);

    /** 子类实现：处理单个条目，返回保存数量_0成功, 0跳过, <0失败_*/
    protected abstract int processOne(S item);

    // ── 公开方法 ────────────────────────────────────────────

    public Long executeAsync(Map<String, Object> params, String triggerType) {
        SysCollectTaskEntity task = createTask(params, triggerType);
        Long taskId = task.getId();

        int[] counters = {0, 0, 0}; // total, success, fail
        S[] items = resolveItems(params);
        counters[0] = items.length;

        updateProgress(taskId, "running", counters[0], 0, 0, 0, "开始执行");

        try {
            for (int i = 0; i < items.length; i++) {
                S item = items[i];
                long startMs = System.currentTimeMillis();
                updateProgress(taskId, "running", counters[0], counters[1], counters[2], 0,
                    "处理_(" + (i + 1) + "/" + items.length + "): " + item);

                try {
                    int saved = processOne(item);
                    int durationMs = (int) (System.currentTimeMillis() - startMs);
                    if (saved > 0) {
                        counters[1] += saved;
                    } else if (saved == 0) {
                        // skip
                    } else {
                        counters[2]++;
                    }
                    saveDetail(taskId, item.toString(), saved > 0 ? "success" : "failed",
                        saved > 0 ? saved : 0, null, durationMs);
                } catch (Exception e) {
                    log.warn("处理失败 [{}] {}: {}", taskType(), item, e.getMessage());
                    counters[2]++;
                    int durationMs = (int) (System.currentTimeMillis() - startMs);
                    saveDetail(taskId, item.toString(), "failed", 0, e.getMessage(), durationMs);
                }

                updateProgress(taskId, "running", counters[0], counters[1], counters[2], 0, null);
            }
            completeTask(task, null);
        } catch (Exception e) {
            log.error("任务执行异常: {}", taskType(), e);
            completeTask(task, e.getMessage());
        } finally {
            redisTemplate.expire(PROGRESS_KEY_PREFIX + taskId, PROGRESS_TTL);
        }

        return taskId;
    }

    public CollectTaskProgress getProgress(Long taskId) {
        String key = PROGRESS_KEY_PREFIX + taskId;
        Map<Object, Object> map = redisTemplate.opsForHash().entries(key);
        if (map.isEmpty()) {
            return taskRepository.findById(taskId)
                .map(this::fromEntity)
                .orElse(null);
        }
        double prog = parseInt(map.get("total")) > 0
            ? 100.0 * (parseInt(map.get("success")) + parseInt(map.get("fail"))) / parseInt(map.get("total"))
            : 0;
        return CollectTaskProgress.builder()
            .taskId(taskId)
            .total(parseInt(map.get("total")))
            .success(parseInt(map.get("success")))
            .fail(parseInt(map.get("fail")))
            .skip(parseInt(map.get("skip")))
            .progress(prog)
            .status((String) map.get("status"))
            .message((String) map.get("message"))
            .build();
    }

    // ── 模板工具 ────────────────────────────────────────────

    protected void updateProgress(Long taskId, String status, int total, int success, int fail, int skip, String msg) {
        String key = PROGRESS_KEY_PREFIX + taskId;
        redisTemplate.opsForHash().putAll(key, Map.of(
            "status", status,
            "total", String.valueOf(total),
            "success", String.valueOf(success),
            "fail", String.valueOf(fail),
            "skip", String.valueOf(skip),
            "message", msg != null ? msg : ""
        ));
        redisTemplate.expire(key, PROGRESS_TTL);
    }

    protected void saveDetail(Long taskId, String symbol, String status, int saved, String error, int durationMs) {
        SysCollectTaskDetailEntity detail = SysCollectTaskDetailEntity.builder()
            .taskId(taskId)
            .symbol(symbol)
            .status(status)
            .savedCount(saved)
            .errorMessage(error)
            .durationMs(durationMs)
            .build();
        detailRepository.save(detail);
    }

    // ── 私有工具 ────────────────────────────────────────────

    private SysCollectTaskEntity createTask(Map<String, Object> params, String triggerType) {
        SysCollectTaskEntity task = SysCollectTaskEntity.builder()
            .taskType(taskType())
            .triggerType(triggerType)
            .params(params)
            .status("running")
            .totalCount(0)
            .successCount(0)
            .failCount(0)
            .skipCount(0)
            .startedAt(LocalDateTime.now())
            .build();
        return taskRepository.save(task);
    }

    private void completeTask(SysCollectTaskEntity task, String errorMsg) {
        task.setStatus(errorMsg == null ? "success" : "failed");
        task.setFinishedAt(LocalDateTime.now());
        long ms = Duration.between(task.getStartedAt(), task.getFinishedAt()).toMillis();
        task.setDurationMs((int) ms);
        task.setMessage(errorMsg);

        String key = PROGRESS_KEY_PREFIX + task.getId();
        task.setSuccessCount(parseInt(redisTemplate.opsForHash().get(key, "success")));
        task.setFailCount(parseInt(redisTemplate.opsForHash().get(key, "fail")));
        task.setSkipCount(parseInt(redisTemplate.opsForHash().get(key, "skip")));
        task.setTotalCount(parseInt(redisTemplate.opsForHash().get(key, "total")));

        taskRepository.save(task);
    }

    private CollectTaskProgress fromEntity(SysCollectTaskEntity e) {
        double prog = e.getTotalCount() > 0
            ? 100.0 * (e.getSuccessCount() + e.getFailCount()) / e.getTotalCount()
            : 0;
        return CollectTaskProgress.builder()
            .taskId(e.getId())
            .taskType(e.getTaskType())
            .status(e.getStatus())
            .total(e.getTotalCount())
            .success(e.getSuccessCount())
            .fail(e.getFailCount())
            .skip(e.getSkipCount())
            .progress(prog)
            .message(e.getMessage())
            .startedAt(e.getStartedAt())
            .finishedAt(e.getFinishedAt())
            .durationMs(e.getDurationMs())
            .build();
    }

    private int parseInt(Object v) {
        if (v == null) return 0;
        try { return Integer.parseInt(v.toString()); }
        catch (Exception e) { return 0; }
    }
}
