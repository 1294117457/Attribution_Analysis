package com.attribution.auth.converter;

import java.util.List;

import com.attribution.auth.entity.RolePO;
import com.attribution.auth.entity.UserPO;
import com.attribution.auth.vo.RoleBriefVO;
import com.attribution.auth.vo.RoleVO;
import com.attribution.auth.vo.UserVO;

/**
 * 用户 / 角色 PO → VO 转换器。
 *
 * <p>按项目规范，转换统一收敛到 {@code converter} 包，Service 层负责调用，
 * Mapper 与 Controller 均不直接做 PO→VO 转换。
 */
public final class UserConverter {

    private UserConverter() {
    }

    /**
     * 用户基础信息搬运（不含角色 / 权限，这两项来自关联表，由 {@link #toVO} 补齐）。
     */
    public static UserVO toVO(UserPO po) {
        if (po == null) return null;
        UserVO vo = new UserVO();
        vo.setId(po.getId());
        vo.setEmail(po.getEmail());
        vo.setNickname(po.getNickname());
        vo.setAvatarUrl(po.getAvatarUrl());
        vo.setIsActive(po.getIsActive());
        vo.setIsVerified(po.getIsVerified());
        vo.setCreatedAt(po.getCreatedAt());
        vo.setLastLoginAt(po.getLastLoginAt());
        // passwordHash / lastLoginIp 等敏感字段故意不拷贝 —— UserVO 中没有这些字段
        return vo;
    }

    /**
     * 用户完整视图：基础信息 + 角色 + 权限。
     *
     * @param po 用户 PO
     * @param roles 该用户拥有的角色（可为空）
     * @param permissionCodes 权限编码集合（可为空）
     */
    public static UserVO toVO(UserPO po, List<RolePO> roles, List<String> permissionCodes) {
        UserVO vo = toVO(po);
        if (vo == null) return null;
        List<RolePO> safeRoles = roles == null ? List.of() : roles;
        vo.setRoles(safeRoles.stream().map(UserConverter::toBriefVO).toList());
        vo.setRoleCodes(safeRoles.stream().map(RolePO::getCode).toList());
        vo.setPermissions(permissionCodes == null ? List.of() : permissionCodes);
        return vo;
    }

    public static List<UserVO> toUserVOList(List<UserPO> pos) {
        return pos == null ? List.of() : pos.stream().map(UserConverter::toVO).toList();
    }

    /** 角色精简视图 */
    public static RoleBriefVO toBriefVO(RolePO po) {
        if (po == null) return null;
        RoleBriefVO vo = new RoleBriefVO();
        vo.setId(po.getId());
        vo.setCode(po.getCode());
        vo.setName(po.getName());
        return vo;
    }

    /** 角色完整视图 */
    public static RoleVO toVO(RolePO po) {
        if (po == null) return null;
        RoleVO vo = new RoleVO();
        vo.setId(po.getId());
        vo.setCode(po.getCode());
        vo.setName(po.getName());
        vo.setDescription(po.getDescription());
        vo.setIsSystem(po.getIsSystem());
        vo.setSortOrder(po.getSortOrder());
        return vo;
    }

    public static List<RoleVO> toRoleVOList(List<RolePO> pos) {
        return pos == null ? List.of() : pos.stream().map(UserConverter::toVO).toList();
    }
}
