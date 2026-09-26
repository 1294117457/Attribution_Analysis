package com.attribution.application.service.collect;

import com.attribution.infrastructure.adapter.collector.akshare.AkShareConceptCollector;
import com.attribution.infrastructure.adapter.collector.tushare.TushareApiClient;
import com.attribution.domain.repository.SysCollectTaskDetailRepository;
import com.attribution.domain.repository.SysCollectTaskRepository;
import com.attribution.application.service.ConceptService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * Concept 概念同步采集任务_ *
 * 支持两种数据源：
 *   - "akshare" _东方财富 HTTP 接口（无需 Python_ *   - "tushare" _Tushare API（需_2000+ 积分_ *   - "both"    _双源并存，按 akshare 优先
 */
@Slf4j
@Component
public class ConceptCollectTask extends BaseCollectTask<String> {

    private final TushareApiClient tushareClient;
    private final AkShareConceptCollector akshareClient;
    private final ConceptService conceptService;

    public ConceptCollectTask(SysCollectTaskRepository taskRepository,
                            SysCollectTaskDetailRepository detailRepository,
                            StringRedisTemplate redisTemplate,
                            TushareApiClient tushareClient,
                            AkShareConceptCollector akshareClient,
                            ConceptService conceptService) {
        super(taskRepository, detailRepository, redisTemplate);
        this.tushareClient = tushareClient;
        this.akshareClient = akshareClient;
        this.conceptService = conceptService;
    }

    @Override
    protected String taskType() {
        return "concept_sync";
    }

    @Override
    @SuppressWarnings("unchecked")
    protected String[] resolveItems(java.util.Map<String, Object> params) {
        String source = (String) params.getOrDefault("source", "akshare");
        List<String> codes = (List<String>) params.get("codes");
        if (codes != null && !codes.isEmpty()) {
            return codes.toArray(new String[0]);
        }
        // 全量同步：按 source 触发
        return new String[]{source};
    }

    @Override
    protected int processOne(String item) {
        String source = item;
        if (item.contains(",")) {
            // 指定 codes: source,code1,code2,...
            String[] parts = item.split(",", 2);
            source = parts[0];
            String[] codeArr = parts[1].split(",");
            List<String> codeList = new ArrayList<>();
            for (String c : codeArr) if (!c.isBlank()) codeList.add(c);
            return switch (source) {
                case "akshare" -> {
                    int sum = 0;
                    for (String code : codeList) {
                        String name = conceptService.getAllConcepts(null).stream()
                            .filter(c -> c.getCode().equals(code))
                            .findFirst().map(c -> c.getName()).orElse(code);
                        sum += akshareClient.fetchConceptStocks(code, name);
                    }
                    yield sum;
                }
                case "tushare" -> tushareClient.fetchConceptBatch(codeList);
                default -> tushareClient.fetchConceptBatch(codeList);
            };
        }
        // 全量
        try {
            return switch (source) {
                case "akshare" -> akshareClient.fetchConceptList();
                case "tushare" -> tushareClient.fetchConceptList().size();
                default -> {
                    int n = akshareClient.fetchConceptList();
                    yield n + tushareClient.fetchConceptList().size();
                }
            };
        } catch (Exception e) {
            throw new RuntimeException("概念同步异常: " + e.getMessage(), e);
        }
    }
}
