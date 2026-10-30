package com.attribution.auth.service;

import java.util.List;

import com.attribution.auth.dto.AssignRoleRequest;
import com.attribution.auth.dto.ChangePasswordRequest;
import com.attribution.auth.dto.ForgotResetRequest;
import com.attribution.auth.dto.LoginRequest;
import com.attribution.auth.dto.RegisterRequest;
import com.attribution.auth.dto.ResetPasswordRequest;
import com.attribution.auth.dto.SendCodeRequest;
import com.attribution.auth.dto.UpdateStatusRequest;
import com.attribution.auth.dto.UserQuery;
import com.attribution.auth.vo.CaptchaVO;
import com.attribution.auth.vo.PermissionVO;
import com.attribution.auth.vo.RoleVO;
import com.attribution.auth.vo.SendCodeVO;
import com.attribution.auth.vo.TokenVO;
import com.attribution.auth.vo.UserStatusVO;
import com.attribution.auth.vo.UserVO;
import com.attribution.common.response.PageResult;

/**
 * 认证 / 用户 / 角色 / 权限服务。
 *
 * <p>接口签名统一使用 DTO（入参）与 VO（出参），不暴露 PO 与裸 Map。
 */
public interface AuthService {
    TokenVO login(LoginRequest request);

    TokenVO refresh(String refreshToken);

    void logout(String auth);

    UserVO me(String auth);

    CaptchaVO captcha();

    UserVO register(RegisterRequest request);

    SendCodeVO sendCode(SendCodeRequest request);

    void changePassword(String auth, ChangePasswordRequest request);

    void forgotReset(ForgotResetRequest request);

    PageResult<UserVO> listUsers(UserQuery query);

    UserStatusVO setStatus(int id, UpdateStatusRequest request);

    void resetPassword(int id, ResetPasswordRequest request);

    void assignRole(int userId, AssignRoleRequest request);

    void removeRole(int userId, int roleId);

    List<RoleVO> roles();

    List<PermissionVO> permissions();
}
