package com.attribution.market.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.market.entity.NameChangePO;
import com.baomidou.dynamic.datasource.annotation.DS;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
@DS("raw")
public interface NameChangeMapper extends BaseMapper<NameChangePO> {}
