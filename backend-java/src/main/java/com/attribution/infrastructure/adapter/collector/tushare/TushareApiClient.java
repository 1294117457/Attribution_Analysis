package com.attribution.infrastructure.adapter.collector.tushare;

import com.attribution.infrastructure.config.TushareProperties;
import com.attribution.domain.entity.BaseAdjFactorEntity;
import com.attribution.domain.entity.CapBlockTradeEntity;
import com.attribution.domain.entity.CapHolderNumEntity;
import com.attribution.domain.entity.CapMarginDetailEntity;
import com.attribution.domain.entity.CapMoneyflowEntity;
import com.attribution.domain.entity.CapTopInstEntity;
import com.attribution.domain.entity.CapTopListEntity;
import com.attribution.domain.entity.FinDailyBasicEntity;
import com.attribution.domain.entity.FinReportEntity;
import com.attribution.domain.entity.FinTop10FloatHolderEntity;
import com.attribution.domain.entity.FinTop10HolderEntity;
import com.attribution.domain.entity.MktCalendarEntity;
import com.attribution.domain.entity.MktMarketDailyEntity;
import com.attribution.domain.repository.BaseAdjFactorRepository;
import com.attribution.domain.repository.CapBlockTradeRepository;
import com.attribution.domain.repository.CapHolderNumRepository;
import com.attribution.domain.repository.CapMarginDetailRepository;
import com.attribution.domain.repository.CapMoneyflowRepository;
import com.attribution.domain.repository.CapTopInstRepository;
import com.attribution.domain.repository.CapTopListRepository;
import com.attribution.domain.repository.FinDailyBasicRepository;
import com.attribution.domain.repository.FinReportRepository;
import com.attribution.domain.repository.FinTop10FloatHolderRepository;
import com.attribution.domain.repository.FinTop10HolderRepository;
import com.attribution.domain.repository.MktCalendarRepository;
import com.attribution.domain.repository.MktMarketDailyRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Tushare API HTTP 客户_+ 批量采集方法
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class TushareApiClient {

    private final WebClient tushareWebClient;
    private final TushareProperties properties;

    private final FinDailyBasicRepository finDailyBasicRepository;
    private final FinReportRepository finReportRepository;
    private final FinTop10HolderRepository finTop10HolderRepository;
    private final FinTop10FloatHolderRepository finTop10FloatHolderRepository;
    private final CapMarginDetailRepository capMarginDetailRepository;
    private final CapMoneyflowRepository capMoneyflowRepository;
    private final CapTopListRepository capTopListRepository;
    private final CapTopInstRepository capTopInstRepository;
    private final CapBlockTradeRepository capBlockTradeRepository;
    private final CapHolderNumRepository capHolderNumRepository;
    private final BaseAdjFactorRepository baseAdjFactorRepository;
    private final MktCalendarRepository mktCalendarRepository;
    private final MktMarketDailyRepository mktMarketDailyRepository;

    private static final DateTimeFormatter DF = DateTimeFormatter.BASIC_ISO_DATE;

    // ── 基础调用 ────────────────────────────────────────────

    public TushareResponse call(String apiName, Map<String, Object> params, String fields) {
        Map<String, Object> body = new HashMap<>();
        body.put("api_name", apiName);
        body.put("token", properties.getToken());
        body.put("params", params);
        body.put("fields", fields);
        try {
            return tushareWebClient.post()
                .bodyValue(body)
                .retrieve()
                .bodyToMono(TushareResponse.class)
                .block(Duration.ofMillis(properties.getTimeout()));
        } catch (Exception e) {
            log.error("Tushare API 调用失败: api={}", apiName, e);
            throw new RuntimeException("Tushare API 调用失败: " + e.getMessage(), e);
        }
    }

    public TushareResponse call(String apiName, Map<String, Object> params) {
        return call(apiName, params, "");
    }

    public List<Object[]> parseItems(TushareResponse response) {
        if (response == null || response.getData() == null || response.getData().getItems() == null) {
            return new ArrayList<>();
        }
        List<Object[]> result = new ArrayList<>();
        for (List<Object> item : response.getData().getItems()) {
            result.add(item.toArray(new Object[0]));
        }
        return result;
    }

    public static String formatDate(LocalDate date) {
        return date.format(DF);
    }

    // ── 批量采集方法 ────────────────────────────────────────

    /** 日频估值指_(daily_basic) */
    public int fetchDailyBasicBatch(LocalDate startDate, LocalDate endDate) {
        String fields = "ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio," +
            "pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv";
        TushareResponse resp = call("daily_basic",
            Map.of("start_date", formatDate(startDate), "end_date", formatDate(endDate)),
            fields);
        List<Object[]> items = parseItems(resp);
        int saved = 0;
        for (Object[] row : items) {
            try {
                FinDailyBasicEntity e = FinDailyBasicEntity.builder()
                    .symbol(toStr(row[0]))
                    .tradeDate(LocalDate.parse(toStr(row[1]), DF))
                    .close(toDouble(row[2]))
                    .turnoverRate(toDouble(row[3]))
                    .turnoverRateF(toDouble(row[4]))
                    .volumeRatio(toDouble(row[5]))
                    .pe(toDouble(row[6]))
                    .peTtm(toDouble(row[7]))
                    .pb(toDouble(row[8]))
                    .ps(toDouble(row[9]))
                    .psTtm(toDouble(row[10]))
                    .dvRatio(toDouble(row[11]))
                    .dvTtm(toDouble(row[12]))
                    .totalShare(toDouble(row[13]))
                    .floatShare(toDouble(row[14]))
                    .freeShare(toDouble(row[15]))
                    .totalMv(toDouble(row[16]))
                    .circMv(toDouble(row[17]))
                    .build();
                finDailyBasicRepository.save(e);
                saved++;
            } catch (Exception ex) {
                log.warn("解析 daily_basic 行失_ {}", ex.getMessage());
            }
        }
        log.info("daily_basic 采集完成: {} ", saved);
        return saved;
    }

    /** 财务报表 (fin_report) */
    public int fetchFinReport(String symbol) {
        String fields = "ts_code,ann_date,end_date,report_type,comp_type,basic_eps,diluted_eps," +
            "total_revenue,revenue,operate_profit,total_profit,n_income,n_income_attr_p," +
            "total_assets,total_liab,total_hldr_eqy_exc_min_int," +
            "n_cashflow_act,n_cash_flows_fnc_act,n_cashflow_inv_act";
        Map<String, Object> params = new HashMap<>();
        if (symbol != null && !symbol.equals("all")) {
            params.put("ts_code", symbol);
        }
        TushareResponse resp = call("fin_report", params, fields);
        List<Object[]> items = parseItems(resp);
        int saved = 0;
        for (Object[] row : items) {
            try {
                FinReportEntity e = FinReportEntity.builder()
                    .symbol(toStr(row[0]))
                    .annDate(toDate(row[1]))
                    .endDate(LocalDate.parse(toStr(row[2]), DF))
                    .reportType(toStr(row[3]))
                    .compType(toStr(row[4]))
                    .basicEps(toDouble(row[5]))
                    .dilutedEps(toDouble(row[6]))
                    .totalRevenue(toDouble(row[7]))
                    .revenue(toDouble(row[8]))
                    .operateProfit(toDouble(row[9]))
                    .totalProfit(toDouble(row[10]))
                    .nIncome(toDouble(row[11]))
                    .nIncomeAttrP(toDouble(row[12]))
                    .totalAssets(toDouble(row[13]))
                    .totalLiab(toDouble(row[14]))
                    .totalHldrEqyExcMinInt(toDouble(row[15]))
                    .nCashflowAct(toDouble(row[16]))
                    .nCashFlowsFncAct(toDouble(row[17]))
                    .nCashflowInvAct(toDouble(row[18]))
                    .build();
                finReportRepository.save(e);
                saved++;
            } catch (Exception ex) {
                log.warn("解析 fin_report 行失_ {}", ex.getMessage());
            }
        }
        log.info("fin_report 采集完成: {} ", saved);
        return saved;
    }

    /** 个股资金流向 (moneyflow) */
    public int fetchMoneyflow(String symbol, LocalDate startDate, LocalDate endDate) {
        String fields = "ts_code,trade_date,buy_sm_vol,buy_sm_amount,sell_sm_vol,sell_sm_amount," +
            "buy_md_vol,buy_md_amount,sell_md_vol,sell_md_amount,buy_lg_vol,buy_lg_amount," +
            "sell_lg_vol,sell_lg_amount,buy_elg_vol,buy_elg_amount,sell_elg_vol,sell_elg_amount," +
            "net_mf_vol,net_mf_amount";
        Map<String, Object> params = new HashMap<>();
        params.put("start_date", formatDate(startDate));
        params.put("end_date", formatDate(endDate));
        if (symbol != null) params.put("ts_code", symbol);
        TushareResponse resp = call("moneyflow", params, fields);
        List<Object[]> items = parseItems(resp);
        int saved = 0;
        for (Object[] row : items) {
            try {
                CapMoneyflowEntity e = CapMoneyflowEntity.builder()
                    .symbol(toStr(row[0]))
                    .tradeDate(LocalDate.parse(toStr(row[1]), DF))
                    .buySmVol(toDouble(row[2])).buySmAmount(toDouble(row[3]))
                    .sellSmVol(toDouble(row[4])).sellSmAmount(toDouble(row[5]))
                    .buyMdVol(toDouble(row[6])).buyMdAmount(toDouble(row[7]))
                    .sellMdVol(toDouble(row[8])).sellMdAmount(toDouble(row[9]))
                    .buyLgVol(toDouble(row[10])).buyLgAmount(toDouble(row[11]))
                    .sellLgVol(toDouble(row[12])).sellLgAmount(toDouble(row[13]))
                    .buyElgVol(toDouble(row[14])).buyElgAmount(toDouble(row[15]))
                    .sellElgVol(toDouble(row[16])).sellElgAmount(toDouble(row[17]))
                    .netMfVol(toDouble(row[18])).netMfAmount(toDouble(row[19]))
                    .build();
                capMoneyflowRepository.save(e);
                saved++;
            } catch (Exception ex) {
                log.warn("解析 moneyflow 行失_ {}", ex.getMessage());
            }
        }
        log.info("moneyflow 采集完成: {} ", saved);
        return saved;
    }

    /** 概念列表 (concept) - 返回原始数据供外部处_*/
    public List<Object[]> fetchConceptList() {
        String fields = "code,name,market";
        TushareResponse resp = call("concept", Map.of(), fields);
        log.info("concept 列表采集完成: {} ", resp != null && resp.getData() != null ? resp.getData().getItems().size() : 0);
        return parseItems(resp);
    }

    public int fetchConceptBatch(List<String> codes) {
        int total = 0;
        for (String code : codes) {
            try {
                String fields = "ts_code,concept_name";
                TushareResponse resp = call("concept_detail", Map.of("id", code), fields);
                total += parseItems(resp).size();
            } catch (Exception e) {
                log.warn("fetchConceptBatch 失败: code={}", code, e);
            }
        }
        return total;
    }

    // ── 工具方法 ────────────────────────────────────────────

    private String toStr(Object v) {
        return v == null ? null : v.toString();
    }

    private Double toDouble(Object v) {
        if (v == null) return null;
        if (v instanceof Number) return ((Number) v).doubleValue();
        try { return Double.parseDouble(v.toString()); } catch (Exception e) { return null; }
    }

    private LocalDate toDate(Object v) {
        if (v == null) return null;
        try { return LocalDate.parse(v.toString(), DF); } catch (Exception e) { return null; }
    }
}
