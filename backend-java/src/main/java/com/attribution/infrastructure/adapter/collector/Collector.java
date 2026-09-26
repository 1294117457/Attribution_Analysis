package com.attribution.infrastructure.adapter.collector;

import com.attribution.interfaces.dto.kline.KlineCollectVO;

import java.time.LocalDate;

/**
 * 数据采集器接_ */
public interface Collector {

    /**
     * 采集器名_     */
    String name();

    /**
     * 采集单只股票_K 线数据（实现方负责入库）
     */
    KlineCollectVO collect(String symbol, int days);

    /**
     * 采集并返回保存数_(_Task 模板调用)
     */
    default int collectCount(String symbol, int days) {
        KlineCollectVO vo = collect(symbol, days);
        return vo != null ? vo.getSaved() : 0;
    }

    /**
     * 计算采集时间范围
     */
    default LocalDate[] calculateRange(int days) {
        LocalDate end = LocalDate.now();
        LocalDate start = end.minusDays(days);
        return new LocalDate[]{start, end};
    }
}
