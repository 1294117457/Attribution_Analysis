package com.attribution.auth.vo;

import java.time.LocalDateTime;
import java.util.List;

import lombok.Data;

/**
 * 用户视图对象（出参契约）。
 *
 * <p>字段与前端 {@code frontend/src/views/auth/api.ts} 的 UserInfo 1:1 对应。
 *
 * <p>注意：{@code passwordHash} / {@code lastLoginIp} 等敏感或内部字段故意不出现在本类中，
 * 由 UserConverter 负责裁剪。
 */
@Data
public class UserVO {
    private Integer id;
    private String email;
    private String nickname;
    private String avatarUrl;
    private Boolean isActive;
    private Boolean isVerified;
    private List<RoleBriefVO> roles;
    private List<String> roleCodes;
    private List<String> permissions;
    private LocalDateTime createdAt;
    private LocalDateTime lastLoginAt;
}
