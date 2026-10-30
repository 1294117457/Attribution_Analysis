package com.attribution.market.service;

import com.attribution.common.response.PageResult;
import com.attribution.market.dto.KlineQuery;
import com.attribution.market.vo.KlineDeleteVO;
import com.attribution.market.vo.KlineStatsVO;
import com.attribution.market.vo.KlineVO;

/**
 * K 线服务。
 *
 * <p>接口签名统一使用 DTO（入参）与 VO（出参），不暴露 PO 与裸 Map。
 */
public interface KlineService {
    PageResult<KlineVO> list(String symbol, KlineQuery query);

    KlineStatsVO stats(String symbol);

    KlineVO one(String symbol, String tradeDate);

    KlineDeleteVO deleteAll(String symbol);

    KlineDeleteVO deleteOne(String symbol, String tradeDate);
}
