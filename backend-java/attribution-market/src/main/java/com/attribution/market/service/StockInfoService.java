package com.attribution.market.service;

import java.util.List;
import java.util.Map;

import com.attribution.common.response.PageResult;
import com.attribution.market.dto.StockPanelQuery;
import com.attribution.market.vo.StockBriefVO;
import com.attribution.market.vo.StockInfoVO;
import com.attribution.market.vo.StockMetaVO;
import com.attribution.market.vo.StockPanelVO;

/**
 * 股票基础信息服务。
 *
 * <p>接口签名统一使用 DTO（入参）与 VO（出参），不暴露 PO 与裸 Map。
 */
public interface StockInfoService {
    StockMetaVO meta();

    StockInfoVO get(String symbol);

    PageResult<StockPanelVO> page(StockPanelQuery query);

    /**
     * 批量取股票基础信息摘要（symbol → name/industry/market/exchange）。
     *
     * <p>供其他模块（如自选池）复用，避免跨模块直接调用 Mapper。
     *
     * @param symbols 股票代码列表，为空时返回空 Map
     * @return symbol → 基础信息摘要；基础信息表中无记录的代码不会出现在结果中
     */
    Map<String, StockBriefVO> briefs(List<String> symbols);
}
