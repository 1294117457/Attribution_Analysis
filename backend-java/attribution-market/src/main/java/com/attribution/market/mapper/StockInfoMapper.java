package com.attribution.market.mapper;

import java.math.BigDecimal;
import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.attribution.market.entity.StockInfoPO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

/**
 * 股票基础信息 Mapper（**采集库** raw_data）。
 *
 * <p>基表 {@code fundamental_stock_basic} 在 raw_data 库，由 Collector 独占写入，Java 只读。
 *
 * <p>★ 池归属查询在 {@link PoolMembershipQueryMapper}（业务库），本接口不跨库。
 */
@Mapper
@DS("raw")
public interface StockInfoMapper extends BaseMapper<StockInfoPO> {

    /**
     * 批量取股票所属概念（联查 fundamental_concept_member + fundamental_concept，均在 raw_data）。
     *
     * @param symbols 股票代码列表
     * @return 视图行：symbol / concept_id / name / source / concept_type
     */
    List<ConceptBriefRow> selectConceptBriefs(@Param("symbols") List<String> symbols);

    /** 按概念 ID 取成员股票代码 */
    List<String> selectSymbolsByConceptId(@Param("conceptId") Integer conceptId);

    /** 按总市值下限过滤股票代码 */
    List<String> selectSymbolsByMinTotalMv(@Param("minTotalMv") Double minTotalMv);

    /**
     * 批量取股票面板所需的统计指标（一次查询替代 N+1）。
     *
     * <p>每只股票返回：K 线记录数 / K 线最早与最晚日期 / 最新一条 daily_basic 估值 /
     * 最新一期合并报表净利润率。原先由 Service 层逐行循环查询 5 次，现下沉为单次聚合查询。
     *
     * @param symbols 股票代码列表
     * @return 视图行，与入参 symbols 一一对应（无数据时该股票不出现在结果中）
     */
    List<StockStatRow> selectStockStats(@Param("symbols") List<String> symbols);

    /** 概念简略视图行 */
    class ConceptBriefRow {
        private String symbol;
        private Integer conceptId;
        private String name;
        private String source;
        private String conceptType;

        public String getSymbol() {
            return symbol;
        }

        public void setSymbol(String symbol) {
            this.symbol = symbol;
        }

        public Integer getConceptId() {
            return conceptId;
        }

        public void setConceptId(Integer conceptId) {
            this.conceptId = conceptId;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public String getSource() {
            return source;
        }

        public void setSource(String source) {
            this.source = source;
        }

        public String getConceptType() {
            return conceptType;
        }

        public void setConceptType(String conceptType) {
            this.conceptType = conceptType;
        }
    }

    /**
     * 股票面板统计视图行。
     *
     * <p>字段对应原 Service 层逐行查询的 5 个结果：K 线数量、K 线起止、最新估值、最新净利率。
     */
    class StockStatRow {
        private String symbol;
        private Long recordCount;
        private String klineStart;
        private String klineEnd;
        private BigDecimal latestClose;
        private BigDecimal totalMv;
        private BigDecimal peTtm;
        private BigDecimal profitMargin;

        public String getSymbol() {
            return symbol;
        }

        public void setSymbol(String symbol) {
            this.symbol = symbol;
        }

        public Long getRecordCount() {
            return recordCount;
        }

        public void setRecordCount(Long recordCount) {
            this.recordCount = recordCount;
        }

        public String getKlineStart() {
            return klineStart;
        }

        public void setKlineStart(String klineStart) {
            this.klineStart = klineStart;
        }

        public String getKlineEnd() {
            return klineEnd;
        }

        public void setKlineEnd(String klineEnd) {
            this.klineEnd = klineEnd;
        }

        public BigDecimal getLatestClose() {
            return latestClose;
        }

        public void setLatestClose(BigDecimal latestClose) {
            this.latestClose = latestClose;
        }

        public BigDecimal getTotalMv() {
            return totalMv;
        }

        public void setTotalMv(BigDecimal totalMv) {
            this.totalMv = totalMv;
        }

        public BigDecimal getPeTtm() {
            return peTtm;
        }

        public void setPeTtm(BigDecimal peTtm) {
            this.peTtm = peTtm;
        }

        public BigDecimal getProfitMargin() {
            return profitMargin;
        }

        public void setProfitMargin(BigDecimal profitMargin) {
            this.profitMargin = profitMargin;
        }
    }
}
