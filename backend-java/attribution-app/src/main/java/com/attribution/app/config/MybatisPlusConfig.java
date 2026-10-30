package com.attribution.app.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.BlockAttackInnerInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;

/**
 * MyBatis-Plus 插件配置。
 *
 * <p>分页插件是 {@code Page<T>} 生效的前提：未注册时 {@code selectPage} 不会追加 LIMIT/OFFSET，
 * 会把全表数据一次性拉回内存。Service 层的分页必须依赖此插件，禁止用 {@code .last("LIMIT ... OFFSET ...")}
 * 手写分页片段（见 docs/规范文档/纵向分层规范/Service层规范.md §3.1）。
 */
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        // 分页插件：单页上限 10000，需 ≥ 业务允许的最大单次取数（K 线 3650 根 / 股票全量 10000 条）
        PaginationInnerInterceptor pagination = new PaginationInnerInterceptor(DbType.POSTGRE_SQL);
        pagination.setMaxLimit(10000L);
        pagination.setOverflow(false);
        interceptor.addInnerInterceptor(pagination);

        // 攻击防护：阻断全表 update/delete
        interceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());

        return interceptor;
    }
}
