鉴权服务负责
    账号相关的注册、登录
    token的派发
    rbac权限的控制
    账户的管理，信息、禁用等


用Authorization Code 

oauth服务下发accesstoken,refreashtoken,idtoken,
然后业务端有鉴权模块

accesstoken鉴权，refreshtoken前端刷新用的，idtoken展示用户用的

业务端：客户端OIDC跳转+换token，后端JWKS校验

PKCE：code_verifier,code_challenge，code
    verifier和challenge就是客户端生成的一次性凭证和oauth服务交换了code然后，携带code跳转到具体业务url，然后用code交换三个token对吗
JWKS:验证token的工具

    Oauth的私钥签发了三个token给业务端，业务端从oauth获取公开的jwks来校验三个token



就是统一登录端，授权服务端，业务客户端，业务服务端

其中统一登录端基于pkce从授权服务端获取code，然后重定向到业务客户端

业务客户端基于code从授权服务端获取三个token，然后后续就是使用三个token来进行相关权限的功能对吗

Keycloak
Java
⭐⭐⭐⭐⭐
生产级 SSO + 用户管理 ✅