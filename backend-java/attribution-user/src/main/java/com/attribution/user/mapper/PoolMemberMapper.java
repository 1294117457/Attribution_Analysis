package com.attribution.user.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.attribution.user.entity.PoolMemberPO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
public interface PoolMemberMapper extends BaseMapper<PoolMemberPO> {

    /**
     * 批量统计各池的成员数（一次查询替代 Service 层逐池 count）。
     *
     * @param poolIds 池 ID 列表
     * @return 视图行：pool_id / member_count
     */
    List<PoolMemberCountRow> selectMemberCounts(@Param("poolIds") List<Integer> poolIds);

    /**
     * 批量查询指定池中已存在的成员代码（一次查询替代逐个 selectCount）。
     *
     * @param poolId 池 ID
     * @param symbols 待检查的股票代码
     * @return 已存在于该池中的股票代码
     */
    List<String> selectExistingSymbols(
            @Param("poolId") Integer poolId, @Param("symbols") List<String> symbols);

    /** 池成员数视图行 */
    class PoolMemberCountRow {
        private Integer poolId;
        private Long memberCount;

        public Integer getPoolId() {
            return poolId;
        }

        public void setPoolId(Integer poolId) {
            this.poolId = poolId;
        }

        public Long getMemberCount() {
            return memberCount;
        }

        public void setMemberCount(Long memberCount) {
            this.memberCount = memberCount;
        }
    }
}
