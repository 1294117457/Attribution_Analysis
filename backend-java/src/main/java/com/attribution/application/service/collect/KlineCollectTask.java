package com.attribution.application.service.collect;

import com.attribution.domain.repository.StockInfoRepository;
import com.attribution.domain.repository.SysCollectTaskDetailRepository;
import com.attribution.domain.repository.SysCollectTaskRepository;
import com.attribution.application.service.CollectorRegistry;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * K线日频数据采集任_ */
@Slf4j
@Component
public class KlineCollectTask extends BaseCollectTask<String> {

    private final CollectorRegistry collectorRegistry;
    private final StockInfoRepository stockInfoRepository;

    public KlineCollectTask(SysCollectTaskRepository taskRepository,
                           SysCollectTaskDetailRepository detailRepository,
                           StringRedisTemplate redisTemplate,
                           CollectorRegistry collectorRegistry,
                           StockInfoRepository stockInfoRepository) {
        super(taskRepository, detailRepository, redisTemplate);
        this.collectorRegistry = collectorRegistry;
        this.stockInfoRepository = stockInfoRepository;
    }

    @Override
    protected String taskType() {
        return "kline_daily";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected String[] resolveItems(java.util.Map<String, Object> params) {
        List<String> symbols = (List<String>) params.get("symbols");
        if (symbols != null && !symbols.isEmpty()) {
            return symbols.toArray(new String[0]);
        }
        return stockInfoRepository.findAll().stream()
            .map(s -> s.getSymbol())
            .toArray(String[]::new);
    }

    @Override
    protected int processOne(String symbol) {
        int days = 500;
        try {
            return collectorRegistry.getKlineCollector().collectCount(symbol, days);
        } catch (Exception e) {
            throw new RuntimeException("K线采集异_ " + e.getMessage(), e);
        }
    }
}
