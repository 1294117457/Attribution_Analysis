package com.attribution.market.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.market.entity.TopListPO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
@DS("raw")
public interface TopListMapper extends BaseMapper<TopListPO> {}
