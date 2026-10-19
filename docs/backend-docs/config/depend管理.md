
1.依赖的初始化
    进程启动时，加载环境配置，创建engine，创建db的asyncSessionFactory
    此时dbsession的工厂创建好，内部用yield/await+try/except/finally来实现session的相关操作
2.Depends注入
    ①route注入dbsession和svc，然后svc再次注入dbsession和②route注入svc，svc注入dbsession
    ①和②的效果是一样的，但是②更标准，边界清晰
3.依赖存放位置
    dependcy_cache的dict，fastapi内部维护的，请求级别
    另外还有contextvars.Context，Python的contextvars模块，进程级概念，task隔离

4.请求结束
    svc返回结果或者抛出异常
    dbsession从yield状态返回，继续后续的commit和close等操作


数据库/redis
    db是工厂模式，每次派发一个session，具体session是否用池复用工厂内部设置
    db工厂模式：有状态（事务），每个请求有各自的commit/rollback
        事务边界，隔离级别，回滚，死锁
    redis是单例client模式，各个地方都用同一个client来用redis缓存
    redis单例：无状态（事务）,多个命令

数据库的asynccontextmanager装饰器
    也就是无装饰器的是用Depend注入的，生命周期跟随请求
    有装饰器的用async with在代码中调用，生命周期跟随async with/

Redis
    redis是单例client模式
    直接import直接调用就好了

关于service和interface
    有用到比如dbsession这种需要Depends注入的资源的service，必须基于Depends注入service到interface中，保证对应都是一个请求的上下文中使用相同资源

    统一所有service都再di中注册后续给interface或者其他模块调用
    
dbsession在service层注入，然后await self._repo.save(bos, session=session)这么使用，保证事务一致性