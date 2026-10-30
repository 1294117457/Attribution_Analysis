package com.attribution.market.mapper;

import org.apache.ibatis.annotations.Mapper;

import com.attribution.market.entity.NewsPO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

@Mapper
public interface NewsMapper extends BaseMapper<NewsPO> {}
