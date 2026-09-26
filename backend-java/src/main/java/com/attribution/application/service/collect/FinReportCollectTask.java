package com.attribution.application.service.collect;

import com.attribution.domain.repository.SysCollectTaskDetailRepository;
import com.attribution.domain.repository.SysCollectTaskRepository;
import com.attribution.infrastructure.adapter.collector.tushare.TushareApiClient;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 财务报表采集任务 (fin_report)
 */
@Slf4j
@Component
public class FinReportCollectTask extends BaseCollectTask<String> {

    private final TushareApiClient tushareClient;

    public FinReportCollectTask(SysCollectTaskRepository taskRepository,
                               SysCollectTaskDetailRepository detailRepository,
                               StringRedisTemplate redisTemplate,
                               TushareApiClient tushareClient) {
        super(taskRepository, detailRepository, redisTemplate);
        this.tushareClient = tushareClient;
    }

    @Override
    protected String taskType() {
        return "fin_report";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected String[] resolveItems(java.util.Map<String, Object> params) {
        List<String> symbols = (List<String>) params.get("symbols");
        if (symbols != null && !symbols.isEmpty()) {
            return symbols.toArray(new String[0]);
        }
        return new String[]{"all"};
    }

    @Override
    protected int processOne(String symbol) {
        try {
            return tushareClient.fetchFinReport(symbol.equals("all") ? null : symbol);
        } catch (Exception e) {
            throw new RuntimeException("财务报表采集异常: " + e.getMessage(), e);
        }
    }
}
