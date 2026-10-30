package com.attribution.user.vo;

import java.util.List;

import lombok.Data;

/** 池详情视图对象（池 + 成员列表） */
@Data
public class PoolDetailVO extends PoolVO {
    private List<PoolMemberVO> members;
}
