package com.attribution.concept.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.concept.entity.ConceptIndexPO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
@DS("raw")
public interface ConceptIndexMapper extends BaseMapper<ConceptIndexPO> {}
