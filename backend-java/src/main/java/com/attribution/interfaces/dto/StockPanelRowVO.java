package com.attribution.interfaces.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDate;
import java.util.List;

/**
 * 股票面板快照 — 聚合多表数据
 *
 * 字段命名：序列化时全部 snake_case，对齐前端 StockInfo 接口。
 * - snake_case 用 @JsonProperty 标注（精确控制，避免全局配置副作用）
 * - DB 中不存在的列（pre_close/change/turnover_rate/profit_margin）固定返回 null
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockPanelRowVO {

    // ── 基本信息 ──────────────────────────────
    @JsonProperty("symbol")    private String symbol;
    @JsonProperty("ts_code")   private String tsCode;
    @JsonProperty("name")      private String name;
    @JsonProperty("area")      private String area;
    @JsonProperty("industry")  private String industry;
    @JsonProperty("market")    private String market;
    @JsonProperty("exchange")  private String exchange;
    @JsonProperty("list_date") private LocalDate listDate;
    @JsonProperty("delist_date") private LocalDate delistDate;
    @JsonProperty("list_status") private String listStatus;
    @JsonProperty("is_hs")     private String isHs;
    @JsonProperty("act_name")  private String actName;
    @JsonProperty("act_ent_type") private String actEntType;

    // ── 当日行情（DB 真实存在的列） ─────────────
    @JsonProperty("trade_date") private LocalDate tradeDate;
    @JsonProperty("close")     private Double close;
    @JsonProperty("open")      private Double open;
    @JsonProperty("high")      private Double high;
    @JsonProperty("low")       private Double low;
    @JsonProperty("volume")    private Long volume;
    @JsonProperty("amount")    private Double amount;
    @JsonProperty("change_pct") private Double pctChange;

    // 前端 StockInfo 要的别名（=close）
    @JsonProperty("latest_close") private Double latestClose;

    // DB 中不存在的列（固定 null，避免前端渲染 NPE）
    @JsonProperty("pre_close")    private Double preClose;     // null
    @JsonProperty("change")       private Double change;       // null
    @JsonProperty("turnover_rate") private Double turnoverRate; // null

    // ── 估值（来自 fin_daily_basics） ──────────
    @JsonProperty("pe")           private Double pe;
    @JsonProperty("pe_ttm")       private Double peTtm;
    @JsonProperty("pb")           private Double pb;
    @JsonProperty("ps")           private Double ps;
    @JsonProperty("ps_ttm")       private Double psTtm;
    @JsonProperty("dv_ratio")     private Double dvRatio;
    @JsonProperty("dv_ttm")       private Double dvTtm;
    @JsonProperty("total_mv")     private Double totalMv;
    @JsonProperty("circ_mv")      private Double circMv;
    @JsonProperty("total_share")  private Double totalShare;
    @JsonProperty("float_share")  private Double floatShare;

    // DB fin_reports 中无此列（固定 null）
    @JsonProperty("profit_margin") private Double profitMargin;

    // ── 技术指标 ─────────────────────────────
    @JsonProperty("ma5")       private Double ma5;
    @JsonProperty("ma10")      private Double ma10;
    @JsonProperty("ma20")      private Double ma20;
    @JsonProperty("ma60")      private Double ma60;
    @JsonProperty("ema12")     private Double ema12;
    @JsonProperty("ema26")     private Double ema26;
    @JsonProperty("macd_bar")  private Double macd;       // macd_bar 别名
    @JsonProperty("macd_dif")  private Double macdDiff;
    @JsonProperty("macd_dea")  private Double macdDea;
    @JsonProperty("rsi6")      private Double rsi6;
    @JsonProperty("rsi12")     private Double rsi12;
    @JsonProperty("rsi24")     private Double rsi24;
    @JsonProperty("kdj_k")     private Double kdjK;
    @JsonProperty("kdj_d")     private Double kdjD;
    @JsonProperty("kdj_j")     private Double kdjJ;
    @JsonProperty("boll_mid")  private Double bollMid;
    @JsonProperty("boll_up")   private Double bollUpper;
    @JsonProperty("boll_dn")   private Double bollLower;

    // ── 资金 ─────────────────────────────────
    @JsonProperty("net_mf_amount") private Double netMfAmount;
    @JsonProperty("net_mf_vol")    private Double netMfVol;

    // ── 信号 ─────────────────────────────────
    @JsonProperty("signals") private List<String> signals;

    // ── K 线统计（with_pools=true 时附带）────
    @JsonProperty("record_count") private Long recordCount;
    @JsonProperty("kline_start")  private String klineStart;
    @JsonProperty("kline_end")    private String klineEnd;

    // ── 关联 ─────────────────────────────────
    @JsonProperty("pools")    private List<PoolBriefVO> pools;
    @JsonProperty("concepts") private List<ConceptBriefVO> concepts;
}
