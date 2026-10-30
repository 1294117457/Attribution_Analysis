package com.attribution.concept.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.concept.entity.ConceptSnapshotPO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
@DS("raw")
public interface ConceptSnapshotMapper extends BaseMapper<ConceptSnapshotPO> {}
