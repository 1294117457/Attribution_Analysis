package com.attribution.application.service.collect;

import com.attribution.domain.repository.SysCollectTaskDetailRepository;
import com.attribution.domain.repository.SysCollectTaskRepository;
import com.attribution.infrastructure.adapter.collector.tushare.TushareApiClient;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.List;

/**
 * 日频估值指标采集任_(daily_basic)
 */
@Slf4j
@Component
public class DailyBasicCollectTask extends BaseCollectTask<String> {

    private final TushareApiClient tushareClient;

    public DailyBasicCollectTask(SysCollectTaskRepository taskRepository,
                               SysCollectTaskDetailRepository detailRepository,
                               StringRedisTemplate redisTemplate,
                               TushareApiClient tushareClient) {
        super(taskRepository, detailRepository, redisTemplate);
        this.tushareClient = tushareClient;
    }

    @Override
    protected String taskType() {
        return "daily_basic";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected String[] resolveItems(java.util.Map<String, Object> params) {
        LocalDate endDate = params.get("end_date") != null
            ? LocalDate.parse(params.get("end_date").toString())
            : LocalDate.now();
        LocalDate startDate = params.get("start_date") != null
            ? LocalDate.parse(params.get("start_date").toString())
            : endDate.minusYears(1);

        List<String> symbols = (List<String>) params.get("symbols");
        if (symbols != null && !symbols.isEmpty()) {
            return symbols.toArray(new String[0]);
        }
        // 按交易日批量采集
        return new String[]{startDate + "," + endDate};
    }

    @Override
    protected int processOne(String dateRange) {
        String[] parts = dateRange.split(",");
        LocalDate start = LocalDate.parse(parts[0]);
        LocalDate end = LocalDate.parse(parts[1]);
        try {
            return tushareClient.fetchDailyBasicBatch(start, end);
        } catch (Exception e) {
            throw new RuntimeException("日频估值采集异_ " + e.getMessage(), e);
        }
    }
}
