package com.attribution.market.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.attribution.market.mapper.row.StockPoolMembershipRow;

/**
 * 股票所属自选池查询（**业务库** attribution）。
 *
 * <p>★ 为什么不放在 {@link StockInfoMapper} 里：{@code StockInfoMapper} 的基表
 * {@code fundamental_stock_basic} 在采集库 raw_data，而本 Mapper 查的是业务库的
 * {@code stock_pool_members} + {@code stock_pools} —— 一个 Mapper 只能访问一个库
 * （规范：docs/规范文档/多库分工与数据源规范.md §2.1 铁律 1）。
 *
 * <p>★ 本接口**故意不标** {@code @DS}：走默认数据源 {@code biz}（业务库）。
 */
@Mapper
public interface StockPoolMembershipQueryMapper {

    /**
     * 批量取股票所属自选池（联查 stock_pool_members + stock_pools）。
     *
     * @param symbols 股票代码列表，为空时返回空列表
     * @return 视图行：symbol / pool_id / name / pool_type
     */
    List<StockPoolMembershipRow> selectPoolMemberships(@Param("symbols") List<String> symbols);
}
