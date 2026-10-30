package com.attribution.auth.converter;

import java.util.List;

import com.attribution.auth.entity.PermissionPO;
import com.attribution.auth.vo.PermissionVO;

/** 权限 PO → VO 转换器 */
public final class PermissionConverter {

    private PermissionConverter() {
    }

    public static PermissionVO toVO(PermissionPO po) {
        if (po == null) return null;
        PermissionVO vo = new PermissionVO();
        vo.setId(po.getId());
        vo.setCode(po.getCode());
        vo.setResource(po.getResource());
        vo.setAction(po.getAction());
        vo.setName(po.getName());
        vo.setDescription(po.getDescription());
        return vo;
    }

    public static List<PermissionVO> toPermissionVOList(List<PermissionPO> pos) {
        return pos == null ? List.of() : pos.stream().map(PermissionConverter::toVO).toList();
    }
}
