package com.attribution.market.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.market.entity.Top10FloatPO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
@DS("raw")
public interface Top10FloatMapper extends BaseMapper<Top10FloatPO> {}
