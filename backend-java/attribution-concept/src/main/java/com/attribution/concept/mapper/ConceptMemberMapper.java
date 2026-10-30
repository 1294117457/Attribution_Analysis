package com.attribution.concept.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.attribution.concept.entity.ConceptMemberPO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
public interface ConceptMemberMapper extends BaseMapper<ConceptMemberPO> {

    /**
     * 批量取股票所属自选池（跨表联查 stock_pool_members + stock_pools）。
     *
     * @param symbols 股票代码列表
     */
    List<PoolMembershipRow> selectPoolMemberships(@Param("symbols") List<String> symbols);

    /** 池归属视图行 */
    class PoolMembershipRow {
        private String symbol;
        private Integer poolId;
        private String name;
        private String poolType;

        public String getSymbol() {
            return symbol;
        }

        public void setSymbol(String symbol) {
            this.symbol = symbol;
        }

        public Integer getPoolId() {
            return poolId;
        }

        public void setPoolId(Integer poolId) {
            this.poolId = poolId;
        }

        public String getName() {
            return name;
        }

        public void setName(String name) {
            this.name = name;
        }

        public String getPoolType() {
            return poolType;
        }

        public void setPoolType(String poolType) {
            this.poolType = poolType;
        }
    }
}
