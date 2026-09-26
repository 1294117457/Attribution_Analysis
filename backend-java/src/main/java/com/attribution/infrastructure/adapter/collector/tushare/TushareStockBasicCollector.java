package com.attribution.infrastructure.adapter.collector.tushare;

import com.attribution.infrastructure.adapter.collector.Collector;
import com.attribution.domain.entity.StockInfoEntity;
import com.attribution.interfaces.dto.kline.KlineCollectVO;
import com.attribution.domain.repository.StockInfoRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Tushare 股票基础信息采集_ */
@Component
@RequiredArgsConstructor
@Slf4j
public class TushareStockBasicCollector implements Collector {

    private final TushareApiClient apiClient;
    private final StockInfoRepository stockInfoRepository;
    private final com.attribution.application.service.CollectorRegistry collectorRegistry;

    @PostConstruct
    public void register() {
        collectorRegistry.register("stock_basic", this);
    }

    @Override
    public String name() {
        return "Tushare";
    }

    @Override
    public KlineCollectVO collect(String symbol, int days) {
        return KlineCollectVO.builder().symbol(symbol).build();
    }

    public int collectAll() {
        Map<String, Object> params = new HashMap<>();
        params.put("list_status", "L");

        TushareResponse response = apiClient.call("stock_basic", params,
            "ts_code,symbol,name,industry,market,exchange,list_date,delist_date,is_hs,act_name,act_ent_type");

        if (response.getCode() != 0) {
            throw new RuntimeException("Tushare API 错误: " + response.getMsg());
        }

        List<Object[]> items = apiClient.parseItems(response);
        int saved = 0;

        for (Object[] row : items) {
            String tsCode = String.valueOf(row[0]);
            String symbol = String.valueOf(row[1]);
            String name = String.valueOf(row[2]);
            String industry = row[3] != null ? String.valueOf(row[3]) : null;
            String market = row[4] != null ? String.valueOf(row[4]) : null;
            String exchange = row[5] != null ? String.valueOf(row[5]) : null;

            LocalDate listDate = null;
            if (row[6] != null && !row[6].toString().isEmpty()) {
                try {
                    listDate = LocalDate.parse(row[6].toString(), java.time.format.DateTimeFormatter.BASIC_ISO_DATE);
                } catch (Exception ignore) {}
            }

            String listStatus = "L";
            String isHs = row[8] != null ? String.valueOf(row[8]) : "N";

            StockInfoEntity entity = stockInfoRepository.findBySymbol(symbol).orElseGet(() ->
                StockInfoEntity.builder().symbol(symbol).listStatus(listStatus).build()
            );
            entity.setTsCode(tsCode);
            entity.setName(name);
            entity.setIndustry(industry);
            entity.setMarket(market);
            entity.setExchange(exchange);
            entity.setListDate(listDate);
            entity.setListStatus(listStatus);
            entity.setIsHs(isHs);
            if (row.length > 9 && row[9] != null) entity.setActName(String.valueOf(row[9]));
            if (row.length > 10 && row[10] != null) entity.setActEntType(String.valueOf(row[10]));

            stockInfoRepository.save(entity);
            saved++;
        }

        log.info("股票基础信息采集完成: {} ", saved);
        return saved;
    }
}
