1.domain
    domain层主要分entity，vo和repository和service
    repository定义持久化接口
    vo用值描述、没有身份的对象，比如两个日期不需要作为对象处理，作为vo同时还可以加上校验等功能
    entity有唯一标识 + 有生命周期 的领域对象
        从数据库读取的数据，核心业务逻辑（实体的状态等修改）
    service
        当一段领域逻辑不适合放在任何一个 entity 上时（跨多对象、通用算法）
        特点：
            - 只依赖 domain（entity / VO / 领域接口），不依赖任何外部 SDK
            - 不查数据库、不调 HTTP、不发 MQ、不取系统时钟
            - 通常没有副作用（无 IO、无状态变更）
            - 可独立单测（不需要 Spring 容器也行）
2.ApplicationService
    用途：编排一个完整业务用例
    特点：
        1. 管事务边界（@Transactional）
        2. 管权限 / 日志 / 缓存 / 幂等
        3. 调外部端口（HTTP / MQ / 调度 / 邮件 / 时钟）
        4. 一个方法对应一个"用户意图"（开始采集、取消操作、查询面板）
    反例：不要在里面写"RSI 怎么算"这种算法

    
    entity：只动自己（"我"的状态、判断、能力）

    ApplicationService：动多个 entity + 外部（"我和世界"的协作）

3.infra
    有adapter，persistence，config，exception
    adapter外部sdk和适配器
    pesistence是domain/repo的持久化实现
    config整体环境配置
    exception全局异常处理
4.share
    放util等通用逻辑

最后依赖方向
    ┌─────────────────┐
    │ interface       │  (controller)
    └────────┬────────┘
            ↓ 调
    ┌─────────────────┐
    │ application     │  (用例编排)
    └────────┬────────┘
            ↓ 调
    ┌─────────────────┐
    │ domain          │  (entity / vo / repository 接口 / service)
    └────────┬────────┘
            ↑ 实现
    ┌─────────────────┐
    │ infrastructure  │  (JPA 实现 / 适配器 / 配置)
    └─────────────────┘


整体架构
    backend-java/src/main/java/com/attribution/
    ├── AttributionApplication.java

    ├── domain/                              ← 不动，扩一个 service/
    │   ├── entity/                          ← 现有
    │   ├── vo/                              ← 现有
    │   ├── repository/                      ← 现有
    │   ├── service/                         ← 🆕 新建
    │   │   ├── indicator/
    │   │   │   ├── SignalDetector.java      ← 从 service/indicator/ 搬过来
    │   │   │   └── TechnicalSummary.java    ← 从 service/indicator/ 搬过来
    │   │   ├── pool/
    │   │   │   └── PoolMembershipDomainService.java   ← 🆕 未来可能新增
    │   │   └── operation/
    │   │       └── OperationStatusDomainService.java  ← 🆕 未来可能新增
    │   └── event/                           ← 🆕 可选，未来
    │
    ├── application/                         ← 🆕 新建
    │   ├── service/
    │   │   ├── PoolOperationAppService.java ← 从 service/ 搬过来（重命名）
    │   │   ├── StockAnalysisAppService.java ← 从 service/ 搬过来（重命名）
    │   │   ├── StockPoolAppService.java     ← 从 service/ 搬过来
    │   │   ├── StockAppService.java         ← 从 service/ 搬过来
    │   │   ├── ConceptAppService.java       ← 从 service/ 搬过来
    │   │   ├── KlineAppService.java         ← 从 service/ 搬过来
    │   │   ├── CollectTaskAppService.java   ← 从 service/ 搬过来
    │   │   └── DatabaseInitializer.java     ← 从 service/ 搬过来（启动用）
    │   ├── dto/                             ← 现有的 dto 整体搬过来（request/response）
    │   ├── assembler/                       ← 🆕 VO 转换（从现有 service 里的 builder 抽出来）
    │   └── port/                            ← 🆕 端口接口（解耦外部）
    │       ├── KlineCollectorPort.java
    │       └── OperationDispatchPort.java
    │
    ├── infrastructure/                      ← 🆕 新建
    │   ├── adapter/                         ← 外部 SDK / 调度器适配器
    │   │   ├── KlineCollectionExecutor.java ← 从 service/ 搬过来
    │   │   ├── OperationDispatcher.java     ← 从 service/ 搬过来
    │   │   ├── CollectorRegistry.java       ← 从 service/ 搬过来
    │   │   └── collect/                     ← 现有的 service/collect/ 整体搬过来
    │   ├── persistence/                     ← 🆕 把 domain/repository 的 JPA 实现放这里
    │   ├── config/                          ← 现有的 config/ 搬过来（Spring 配置）
    │   └── exception/                       ← 现有的 exception/ 搬过来
    │
    ├── controller/                           
    │
    └── shared/                              ← 🆕 通用工具（可选）
        └── utils/
