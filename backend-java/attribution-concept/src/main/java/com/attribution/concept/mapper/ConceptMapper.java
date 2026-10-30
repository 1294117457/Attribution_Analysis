package com.attribution.concept.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.attribution.concept.entity.ConceptPO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
public interface ConceptMapper extends BaseMapper<ConceptPO> {

    /** 按股票代码反查所属概念（联查 concept_member + concept） */
    List<ConceptBriefRow> selectBriefsBySymbol(@Param("symbol") String symbol);

    /** 按股票代码反查概念分组（含入选理由） */
    List<ConceptGroupRow> selectGroupsBySymbol(@Param("symbol") String symbol);

    /** 概念成员数 */
    long countMembers(@Param("conceptId") Integer conceptId);

    /** 成员最近同步时间 */
    String selectMaxSyncedAt();

    /** 概念成员分页查询（联查 stock_info + daily_basic 最新一条） */
    List<ConceptMemberRow> selectMemberRows(
            @Param("conceptId") Integer conceptId, @Param("limit") int limit, @Param("offset") int offset);

    /** 概念简略视图行 */
    class ConceptBriefRow {
        private Integer conceptId;
        private String name;
        private String source;
        private String conceptType;

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

    /** 概念分组视图行 */
    class ConceptGroupRow {
        private Integer conceptId;
        private String indexCode;
        private String name;
        private String source;
        private String conceptType;
        private String description;
        private String reason;

        public Integer getConceptId() {
            return conceptId;
        }

        public void setConceptId(Integer conceptId) {
            this.conceptId = conceptId;
        }

        public String getIndexCode() {
            return indexCode;
        }

        public void setIndexCode(String indexCode) {
            this.indexCode = indexCode;
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

        public String getDescription() {
            return description;
        }

        public void setDescription(String description) {
            this.description = description;
        }

        public String getReason() {
            return reason;
        }

        public void setReason(String reason) {
            this.reason = reason;
        }
    }

    /** 概念成员视图行 */
    class ConceptMemberRow {
        private String symbol;
        private String name;
        private String industry;
        private String market;
        private java.math.BigDecimal latestClose;
        private java.math.BigDecimal totalMv;
        private java.math.BigDecimal peTtm;

        public String getSymbol() {
            return symbol;
        }

        public void setSymbol(String symbol) {
            this.symbol = symbol;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public String getIndustry() {
            return industry;
        }

        public void setIndustry(String industry) {
            this.industry = industry;
        }

        public String getMarket() {
            return market;
        }

        public void setMarket(String market) {
            this.market = market;
        }

        public java.math.BigDecimal getLatestClose() {
            return latestClose;
        }

        public void setLatestClose(java.math.BigDecimal latestClose) {
            this.latestClose = latestClose;
        }

        public java.math.BigDecimal getTotalMv() {
            return totalMv;
        }

        public void setTotalMv(java.math.BigDecimal totalMv) {
            this.totalMv = totalMv;
        }

        public java.math.BigDecimal getPeTtm() {
            return peTtm;
        }

        public void setPeTtm(java.math.BigDecimal peTtm) {
            this.peTtm = peTtm;
        }
    }
}
