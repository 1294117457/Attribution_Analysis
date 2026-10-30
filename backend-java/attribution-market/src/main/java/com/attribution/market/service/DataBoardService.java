package com.attribution.market.service;

import com.attribution.common.response.PageResult;
import com.attribution.market.dto.StockListQuery;
import com.attribution.market.vo.AdjFactorResponseVO;
import com.attribution.market.vo.BlockTradeResponseVO;
import com.attribution.market.vo.DividendResponseVO;
import com.attribution.market.vo.FinReportResponseVO;
import com.attribution.market.vo.HolderNumResponseVO;
import com.attribution.market.vo.MarginResponseVO;
import com.attribution.market.vo.MoneyflowResponseVO;
import com.attribution.market.vo.NameChangeResponseVO;
import com.attribution.market.vo.OverviewVO;
import com.attribution.market.vo.StockAnalysisVO;
import com.attribution.market.vo.StockInfoVO;
import com.attribution.market.vo.StockListItemVO;
import com.attribution.market.vo.SuspendResponseVO;
import com.attribution.market.vo.TechKlineVO;
import com.attribution.market.vo.Top10FloatResponseVO;
import com.attribution.market.vo.Top10HolderResponseVO;
import com.attribution.market.vo.TopInstResponseVO;
import com.attribution.market.vo.TopListResponseVO;
import com.attribution.market.vo.ValuationResponseVO;

/**
 * 数据看板服务。
 *
 * <p>原实现以 {@code list(String kind, String symbol)} 做字符串分发，调用方需硬编码
 * 类型名；此处拆为强类型方法，每个方法对应一个数据面。
 */
public interface DataBoardService {
    TechKlineVO techKline(String symbol, int limit);

    AdjFactorResponseVO adjFactor(String symbol);

    SuspendResponseVO suspend(String symbol);

    NameChangeResponseVO nameChange(String symbol);

    MoneyflowResponseVO moneyflow(String symbol, int days);

    MarginResponseVO margin(String symbol, int days);

    TopListResponseVO topList(String symbol, int days);

    TopInstResponseVO topInst(String symbol, int days);

    BlockTradeResponseVO blockTrade(String symbol, int days);

    HolderNumResponseVO holderNum(String symbol);

    StockInfoVO stockInfo(String symbol);

    ValuationResponseVO dailyBasic(String symbol, int days);

    FinReportResponseVO finReport(String symbol);

    Top10HolderResponseVO top10Holders(String symbol);

    Top10FloatResponseVO top10Float(String symbol);

    DividendResponseVO dividend(String symbol);

    OverviewVO overview(String symbol);

    PageResult<StockListItemVO> stockList(StockListQuery query);

    PageResult<StockListItemVO> stockListAll();

    StockAnalysisVO analysis(String symbol, int days);
}
