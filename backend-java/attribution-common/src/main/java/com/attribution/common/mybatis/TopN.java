package com.attribution.common.mybatis;

import java.util.List;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

/**
 * 「取前 N 行」查询辅助。
 *
 * <p><b>为什么需要它</b>：Service 层过去用 {@code wrapper.last("LIMIT " + n)} 截断结果集，
 * 这把 SQL 片段写进了业务代码，违反 docs/规范文档/纵向分层规范/Service层规范.md §3.1。本类改用
 * MyBatis-Plus 的 {@link Page} 机制，由分页插件（见 {@code MybatisPlusConfig}）在 SQL 层
 * 追加 LIMIT，从而让 Service 层完全不出现 SQL 字符串。
 *
 * <p><b>使用前提</b>：分页插件必须已注册，否则 {@code selectPage} 不会截断数据。
 *
 * <pre>{@code
 * // ❌ 旧写法：Service 层出现 SQL 片段
 * list = mapper.selectList(wrapper.last("LIMIT " + limit));
 *
 * // ✅ 新写法
 * list = TopN.query(mapper, wrapper, limit);
 * }</pre>
 */
public final class TopN {

    /**
     * 分页插件单页上限，超出会被截断。
     *
     * <p>取值需 ≥ 业务允许的最大单次取数（K 线单次最多 3650 根、股票全量列表 10000 条），
     * 否则会静默丢数据。
     */
    private static final long MAX_LIMIT = 10000L;

    private TopN() {}

    /**
     * 按 wrapper 条件取前 {@code limit} 条记录。
     *
     * @param mapper  MyBatis-Plus Mapper
     * @param wrapper 查询条件（由调用方保证排序已设置）
     * @param limit  条数上限，非法值按 1 处理
     * @param <PO>    实体类型
     * @return 记录列表，最多 {@code limit} 条
     */
    public static <PO> List<PO> query(BaseMapper<PO> mapper, LambdaQueryWrapper<PO> wrapper, int limit) {
        int size = Math.max(limit, 1);
        Page<PO> page = new Page<>(1, Math.min(size, MAX_LIMIT));
        // 不需要总数：分页插件据此跳过 COUNT 查询
        page.setSearchCount(false);
        return mapper.selectPage(page, wrapper).getRecords();
    }

    /**
     * 取最新一条记录（等价于 {@code ORDER BY 排序字段 DESC LIMIT 1}）。
     *
     * @param mapper  MyBatis-Plus Mapper
     * @param wrapper 查询条件（由调用方保证排序已设置）
     * @param <PO>    实体类型
     * @return 记录列表，无数据时为空列表
     */
    public static <PO> List<PO> latest(BaseMapper<PO> mapper, LambdaQueryWrapper<PO> wrapper) {
        return query(mapper, wrapper, 1);
    }
}
