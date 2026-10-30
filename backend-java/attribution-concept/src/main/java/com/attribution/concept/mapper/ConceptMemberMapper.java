package com.attribution.concept.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.concept.entity.ConceptMemberPO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

/**
 * 概念成分股 Mapper（**采集库** raw_data）。
 *
 * <p>基表 {@code fundamental_concept_member} 在 raw_data 库，由 Collector 独占写入，Java 只读。
 *
 * <p>★ 池归属查询在 {@link PoolMembershipQueryMapper}（业务库），本接口不跨库。
 */
@Mapper
@DS("raw")
public interface ConceptMemberMapper extends BaseMapper<ConceptMemberPO> {}
