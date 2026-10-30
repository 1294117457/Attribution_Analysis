package com.attribution.auth.service.impl;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

import javax.crypto.SecretKey;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import com.attribution.auth.converter.PermissionConverter;
import com.attribution.auth.converter.UserConverter;
import com.attribution.auth.dto.AssignRoleRequest;
import com.attribution.auth.dto.ChangePasswordRequest;
import com.attribution.auth.dto.ForgotResetRequest;
import com.attribution.auth.dto.LoginRequest;
import com.attribution.auth.dto.RegisterRequest;
import com.attribution.auth.dto.ResetPasswordRequest;
import com.attribution.auth.dto.SendCodeRequest;
import com.attribution.auth.dto.UpdateStatusRequest;
import com.attribution.auth.dto.UserQuery;
import com.attribution.auth.entity.*;
import com.attribution.auth.mapper.*;
import com.attribution.auth.service.AuthService;
import com.attribution.auth.vo.CaptchaVO;
import com.attribution.auth.vo.PermissionVO;
import com.attribution.auth.vo.RoleVO;
import com.attribution.auth.vo.SendCodeVO;
import com.attribution.auth.vo.TokenVO;
import com.attribution.auth.vo.UserStatusVO;
import com.attribution.auth.vo.UserVO;
import com.attribution.common.exception.BusinessException;
import com.attribution.common.response.PageResult;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {
    private final UserMapper userMapper;
    private final RoleMapper roleMapper;
    private final PermissionMapper permissionMapper;
    private final UserRoleMapper userRoleMapper;
    private final RolePermissionMapper rolePermissionMapper;
    private final StringRedisTemplate redis;
    private final JavaMailSender mail;
    private final CaptchaService captchaService;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Value("${jwt.secret:attribution-dev-secret-key-32bytes-min!!}")
    private String secret;

    @Value("${jwt.access-expire:900}")
    private long accessExp;

    @Value("${jwt.refresh-expire:604800}")
    private long refreshExp;

    // ── Redis 工具 ───────────────────────────────────────────

    /**
     * 按模式删除匹配的 key。
     *
     * <p>⚠️ **禁止用 {@code redis.keys(pattern)}**——{@code KEYS} 是 O(N) 且**阻塞** Redis，
     * 在生产环境会拖垮整个实例。这里用 {@code SCAN} 游标分批迭代。
     *
     * <p>规范见 {@code docs/规范文档/横切技术规范/基础设施规范.md} §3.5。
     */
    private void deleteByPattern(String pattern) {
        try (var cursor = redis.scan(ScanOptions.scanOptions().match(pattern).count(100).build())) {
            while (cursor.hasNext()) {
                String key = cursor.next();
                if (key != null) redis.delete(key);
            }
        }
    }

    // ── JWT 工具 ─────────────────────────────────────────────

    private SecretKey key() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    private String jwt(int userId, String type, long expireSeconds) {
        long now = System.currentTimeMillis() / 1000;
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("type", type)
                .issuedAt(new Date(now * 1000))
                .expiration(new Date((now + expireSeconds) * 1000))
                .signWith(key())
                .compact();
    }

    private int uidOf(String auth) {
        if (auth == null || !auth.startsWith("Bearer ")) throw new BusinessException(401, "未登录");
        try {
            String subject =
                    Jwts.parser()
                            .verifyWith(key())
                            .build()
                            .parseSignedClaims(auth.substring(7))
                            .getPayload()
                            .getSubject();
            return Integer.parseInt(subject);
        } catch (Exception e) {
            throw new BusinessException(401, "token无效");
        }
    }

    // ── 用户视图组装 ─────────────────────────────────────────

    /** 取用户拥有的角色 PO 列表 */
    private List<RolePO> rolesOf(int userId) {
        List<UserRolePO> userRoles =
                userRoleMapper.selectList(
                        new LambdaQueryWrapper<UserRolePO>().eq(UserRolePO::getUserId, userId));
        List<Integer> roleIds = userRoles.stream().map(UserRolePO::getRoleId).toList();
        return roleIds.isEmpty() ? List.of() : roleMapper.selectBatchIds(roleIds);
    }

    /** 取角色集合对应的权限编码 */
    private List<String> permissionCodesOf(List<RolePO> roles) {
        if (roles.isEmpty()) return List.of();
        Set<Integer> permissionIds = new LinkedHashSet<>();
        for (RolePO role : roles) {
            rolePermissionMapper
                    .selectList(
                            new LambdaQueryWrapper<RolePermissionPO>()
                                    .eq(RolePermissionPO::getRoleId, role.getId()))
                    .forEach(rolePermission -> permissionIds.add(rolePermission.getPermissionId()));
        }
        if (permissionIds.isEmpty()) return List.of();
        return permissionMapper.selectBatchIds(new ArrayList<>(permissionIds)).stream()
                .map(PermissionPO::getCode)
                .toList();
    }

    /** 组装用户完整视图（含角色 / 权限） */
    private UserVO userView(UserPO user) {
        List<RolePO> roles = rolesOf(user.getId());
        return UserConverter.toVO(user, roles, permissionCodesOf(roles));
    }

    // ── 认证 ─────────────────────────────────────────────────

    @Override
    public TokenVO login(LoginRequest request) {
        captchaService.verify(request.getCaptchaId(), request.getCaptchaCode());
        String email = request.getEmail().toLowerCase().trim();
        UserPO user =
                userMapper.selectOne(
                        new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email));
        if (user == null || !passwordEncoder.matches(request.getPassword(), user.getPasswordHash()))
            throw new BusinessException(401, "用户名或密码错误");
        if (Boolean.FALSE.equals(user.getIsActive())) throw new BusinessException(403, "用户已禁用");

        user.setLastLoginAt(LocalDateTime.now());
        user.setLastLoginIp(request.getClientIp());
        userMapper.updateById(user);

        String accessToken = jwt(user.getId(), "access", accessExp);
        String refreshToken = jwt(user.getId(), "refresh", refreshExp);
        redis.opsForValue()
                .set("refresh:" + user.getId() + ":" + refreshToken, "1", Duration.ofSeconds(refreshExp));

        TokenVO tokenVO = new TokenVO();
        tokenVO.setAccessToken(accessToken);
        tokenVO.setRefreshToken(refreshToken);
        tokenVO.setExpiresIn(accessExp);
        tokenVO.setUserInfo(userView(user));
        return tokenVO;
    }

    @Override
    public TokenVO refresh(String refreshToken) {
        int userId;
        try {
            String subject =
                    Jwts.parser()
                            .verifyWith(key())
                            .build()
                            .parseSignedClaims(refreshToken)
                            .getPayload()
                            .getSubject();
            userId = Integer.parseInt(subject);
        } catch (Exception e) {
            throw new BusinessException(401, "refresh token无效");
        }
        String redisKey = "refresh:" + userId + ":" + refreshToken;
        if (redis.opsForValue().get(redisKey) == null)
            throw new BusinessException(401, "refresh token无效");
        redis.delete(redisKey);

        TokenVO tokenVO = new TokenVO();
        tokenVO.setAccessToken(jwt(userId, "access", accessExp));
        tokenVO.setRefreshToken(jwt(userId, "refresh", refreshExp));
        tokenVO.setExpiresIn(accessExp);
        redis.opsForValue()
                .set(
                        "refresh:" + userId + ":" + tokenVO.getRefreshToken(),
                        "1",
                        Duration.ofSeconds(refreshExp));
        return tokenVO;
    }

    @Override
    public void logout(String auth) {
        int userId = uidOf(auth);
        deleteByPattern("refresh:" + userId + ":*");
    }

    @Override
    public UserVO me(String auth) {
        int userId = uidOf(auth);
        UserPO user = userMapper.selectById(userId);
        if (user == null) throw new BusinessException(401, "token无效");
        return userView(user);
    }

    @Override
    public CaptchaVO captcha() {
        return captchaService.generate();
    }

    // ── 注册 / 验证码 ─────────────────────────────────────────

    @Override
    public UserVO register(RegisterRequest request) {
        String email = request.getEmail().toLowerCase().trim();
        String storedCode = redis.opsForValue().get("email_code:register:" + email);
        if (storedCode == null) throw new BusinessException(400, "验证码已过期,请重新获取");
        if (!storedCode.equals(request.getCode().strip())) throw new BusinessException(400, "验证码错误");
        redis.delete("email_code:register:" + email);

        if (userMapper.selectCount(new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email)) > 0)
            throw new BusinessException(400, "邮箱已注册");

        UserPO user = new UserPO();
        user.setEmail(email);
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        String nickname = request.getNickname();
        user.setNickname(nickname == null || nickname.isBlank() ? email.split("@")[0] : nickname.trim());
        user.setIsActive(true);
        user.setIsVerified(true);
        userMapper.insert(user);

        return UserConverter.toVO(user);
    }

    @Override
    public SendCodeVO sendCode(SendCodeRequest request) {
        captchaService.verify(request.getCaptchaId(), request.getCaptchaCode());
        String email = request.getEmail().toLowerCase().trim();
        String purpose = request.getPurpose() == null ? "register" : request.getPurpose();

        if ("register".equals(purpose)
                && userMapper.selectCount(new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email)) > 0)
            throw new BusinessException(400, "邮箱已注册");
        if ("reset_password".equals(purpose)
                && userMapper.selectCount(new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email)) == 0)
            throw new BusinessException(404, "邮箱未注册");

        String rateLimitKey = "rl:email_code:1m:" + purpose + ":" + email;
        if (redis.opsForValue().get(rateLimitKey) != null)
            throw new BusinessException(400, "验证码发送过于频繁,请 60 秒后再试");
        redis.opsForValue().set(rateLimitKey, "1", Duration.ofSeconds(60));

        String code = String.format("%06d", new Random().nextInt(1000000));
        redis.opsForValue().set("email_code:" + purpose + ":" + email, code, Duration.ofMinutes(5));
        try {
            var message = mail.createMimeMessage();
            message.setRecipients(jakarta.mail.Message.RecipientType.TO, email);
            message.setSubject("[归因分析]验证码");
            message.setText("验证码：" + code + "，5分钟内有效");
            mail.send(message);
        } catch (Exception e) {
            redis.delete("email_code:" + purpose + ":" + email);
            throw new BusinessException(400, "验证码发送失败: " + e.getMessage());
        }
        SendCodeVO sendCodeVO = new SendCodeVO();
        sendCodeVO.setPurpose(purpose);
        return sendCodeVO;
    }

    // ── 密码 ─────────────────────────────────────────────────

    @Override
    public void changePassword(String auth, ChangePasswordRequest request) {
        int userId = uidOf(auth);
        UserPO user = userMapper.selectById(userId);
        if (user == null) throw new BusinessException(401, "token无效");
        if (!passwordEncoder.matches(request.getOldPassword(), user.getPasswordHash()))
            throw new BusinessException(400, "旧密码错误");
        user.setPasswordHash(passwordEncoder.encode(request.getNewPassword()));
        userMapper.updateById(user);
        logout(auth);
    }

    @Override
    public void forgotReset(ForgotResetRequest request) {
        String email = request.getEmail().toLowerCase().trim();
        String storedCode = redis.opsForValue().get("email_code:reset_password:" + email);
        if (storedCode == null) throw new BusinessException(400, "验证码已过期,请重新获取");
        if (!storedCode.equals(request.getCode().strip())) throw new BusinessException(400, "验证码错误");

        UserPO user =
                userMapper.selectOne(new LambdaQueryWrapper<UserPO>().eq(UserPO::getEmail, email));
        if (user == null) throw new BusinessException(404, "邮箱未注册");
        user.setPasswordHash(passwordEncoder.encode(request.getNewPassword()));
        userMapper.updateById(user);
        redis.delete("email_code:reset_password:" + email);
    }

    // ── 用户管理 ─────────────────────────────────────────────

    @Override
    public PageResult<UserVO> listUsers(UserQuery query) {
        var wrapper = new LambdaQueryWrapper<UserPO>();
        if (query.getKeyword() != null && !query.getKeyword().isBlank())
            wrapper.and(
                    condition ->
                            condition
                                    .like(UserPO::getEmail, query.getKeyword())
                                    .or()
                                    .like(UserPO::getNickname, query.getKeyword()));
        if (query.getIsActive() != null) wrapper.eq(UserPO::getIsActive, query.getIsActive());

        var pageParam = new Page<UserPO>(query.getPage(), query.getPageSize());
        userMapper.selectPage(pageParam, wrapper);
        List<UserVO> list =
                pageParam.getRecords().stream().map(this::userView).toList();
        return PageResult.of(pageParam.getTotal(), list, query.getPage(), query.getPageSize());
    }

    @Override
    public UserStatusVO setStatus(int id, UpdateStatusRequest request) {
        UserPO user = userMapper.selectById(id);
        if (user == null) throw new BusinessException(404, "用户不存在");
        boolean isActive = Boolean.TRUE.equals(request.getIsActive());
        user.setIsActive(isActive);
        userMapper.updateById(user);
        if (!isActive) {
            deleteByPattern("refresh:" + id + ":*");
        }
        UserStatusVO statusVO = new UserStatusVO();
        statusVO.setId(user.getId());
        statusVO.setIsActive(isActive);
        return statusVO;
    }

    @Override
    public void resetPassword(int id, ResetPasswordRequest request) {
        UserPO user = userMapper.selectById(id);
        if (user == null) throw new BusinessException(404, "用户不存在");
        user.setPasswordHash(passwordEncoder.encode(request.getNewPassword()));
        userMapper.updateById(user);
        deleteByPattern("refresh:" + id + ":*");
    }

    @Override
    public void assignRole(int userId, AssignRoleRequest request) {
        Integer roleId = request.getRoleId();
        long existing =
                userRoleMapper.selectCount(
                        new LambdaQueryWrapper<UserRolePO>()
                                .eq(UserRolePO::getUserId, userId)
                                .eq(UserRolePO::getRoleId, roleId));
        if (existing == 0) {
            UserRolePO userRole = new UserRolePO();
            userRole.setUserId(userId);
            userRole.setRoleId(roleId);
            userRoleMapper.insert(userRole);
        }
    }

    @Override
    public void removeRole(int userId, int roleId) {
        userRoleMapper.delete(
                new LambdaQueryWrapper<UserRolePO>()
                        .eq(UserRolePO::getUserId, userId)
                        .eq(UserRolePO::getRoleId, roleId));
    }

    @Override
    public List<RoleVO> roles() {
        return UserConverter.toRoleVOList(roleMapper.selectList(null));
    }

    @Override
    public List<PermissionVO> permissions() {
        return PermissionConverter.toPermissionVOList(permissionMapper.selectList(null));
    }
}
