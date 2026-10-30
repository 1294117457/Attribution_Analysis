package com.attribution.market.mapper.row;

import lombok.Data;

/**
 * 股票所属自选池视图行（SQL 结果集，不是任何单表的映射）。
 *
 * <p>对应表：{@code attribution.stock_pool_members} + {@code attribution.stock_pools}（**业务库**）。
 *
 * <p>规范：docs/规范文档/纵向分层规范/Mapper层规范.md §2.4.1（Row 独立成文件，不做 Mapper 接口内部类）。
 */
@Data
public class StockPoolMembershipRow {
    /** 股票代码 */
    private String symbol;

    /** 池 ID */
    private Integer poolId;

    /** 池名称 */
    private String name;

    /** 池类型（custom / default ...） */
    private String poolType;
}
