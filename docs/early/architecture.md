# 系统架构文档

**版本**：v2.0  
**日期**：2026年6月  
**技术栈**：Node.js + Fastify + LangGraph TS + Vue 3

---

## 一、技术选型

### 1.1 后端技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **运行时** | Node.js 20 LTS | JavaScript 运行时，生态成熟 |
| **语言** | TypeScript 5.x | 类型安全，代码提示好 |
| **框架** | Fastify 4.x | 高性能 Web 框架，比 Express 快 2x |
| **AI 编排** | LangGraph TS | 多 Agent 协作编排 |
| **LLM** | OpenAI API / 通义千问 | AI 判断和报告生成 |
| **向量存储** | Qdrant / PGVector | 经验向量存储与相似检索 |
| **数据库** | PostgreSQL 16 | 经验记录、用户反馈、分析历史 |
| **ORM** | Prisma | TypeScript 优先的 ORM |

### 1.2 前端技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **框架** | Vue 3.4+ | 响应式前端框架 |
| **语言** | TypeScript 5.x | 类型安全 |
| **构建** | Vite 5.x | 快速构建工具 |
| **UI 组件** | Element Plus | Vue 3 组件库 |
| **图表** | ECharts 5.x | 瀑布图、折线图、贡献度图 |
| **状态** | Pinia | Vue 3 状态管理 |
| **HTTP** | Axios | API 请求 |

### 1.3 基础设施

| 组件 | 选型 | 说明 |
|------|------|------|
| **容器化** | Docker + Docker Compose | 开发/生产部署 |
| **进程管理** | PM2 | Node.js 进程管理 |
| **反向代理** | Nginx | 生产环境反向代理 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                            │
│  数据上传 → 指标配置 → 看板展示 → 交互式下钻 → 用户反馈        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API 网关层 (Fastify)                          │
│  POST /api/analyze  POST /api/feedback  GET /api/experience     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LangGraph 多 Agent 编排层                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  异常检测    │→ │  归因分析    │→ │  报告生成    │        │
│  │   Agent      │  │   Agent      │  │   Agent      │        │
│  │  (算法+AI)   │  │  (算法+AI)   │  │    (AI)      │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                │                  │                  │
│         └────────────────┴──────────────────┘                  │
│                          │                                      │
│                    经验检索/存储                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       算法引擎层                                 │
│  StatisticalDetector  SignalExtractor  ContributionCalculator   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       数据接入层                                 │
│       CsvAdapter  DatabaseAdapter  ApiAdapter (CalcFi/Binance) │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户上传 CSV/选择数据源
        │
        ▼
┌──────────────────┐
│  Data Adapter    │  统一数据格式
│  (CSV/DB/API)    │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ 异常检测 Agent   │  8种算法 + AI判断
│  (Graph State)   │
└──────────────────┘
        │
   经验匹配? ──── Yes ──── 直接复用结论
        │
        No (继续)
        │
        ▼
┌──────────────────┐
│ 归因分析 Agent   │  基期拆解 + 贡献度
│  (Graph State)   │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ 报告生成 Agent   │  AI 生成业务报告
│  (Graph State)   │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ 经验保存         │  向量化存储
└──────────────────┘
        │
        ▼
    返回前端展示
```

---

## 三、LangGraph Agent 设计

### 3.1 核心状态 (State)

```typescript
// src/agents/types.ts
interface AnalysisState {
  // 输入
  dataset: Dataset;
  metric: string;
  dimensions: string[];
  compareType: 'MONTH_OVER_MONTH' | 'YEAR_OVER_YEAR' | 'PERIOD_OVER_PERIOD';

  // 异常检测结果
  anomaly: {
    isAnomaly: boolean;
    score: number;
    methods: AnomalyMethod[];
    signal: SignalFeatures;
    reason?: string;
  };

  // 归因分析结果
  attribution: {
    contributions: Contribution[];
    totalChange: number;
    topDrivers: string[];
    topDraggers: string[];
  };

  // 经验匹配
  experience: {
    matched: Experience | null;
    confidence: number;
  };

  // AI 报告
  report: {
    summary: string;
    insights: string[];
    suggestions: string[];
  };

  // 元数据
  errors: string[];
  step: string;
}
```

### 3.2 Agent 节点定义

```typescript
// src/agents/index.ts
import { StateGraph } from '@langchain/langgraph';
import { anomalyAgent } from './anomaly';
import { attributionAgent } from './attribution';
import { reportingAgent } from './reporting';
import { experienceNode } from './experience';

// 构建状态图
const workflow = new StateGraph({ channels: AnalysisState })
  // 节点
  .addNode('experience_lookup', experienceNode.lookup)
  .addNode('anomaly_detection', anomalyAgent.detect)
  .addNode('attribution_analysis', attributionAgent.analyze)
  .addNode('report_generation', reportingAgent.generate)
  .addNode('experience_save', experienceNode.save)
  // 边
  .addEdge('__start__', 'experience_lookup')
  .addConditionalEdges('experience_lookup', shouldSkipAnomaly, {
    skip: 'report_generation',
    continue: 'anomaly_detection'
  })
  .addEdge('anomaly_detection', 'attribution_analysis')
  .addEdge('attribution_analysis', 'report_generation')
  .addEdge('report_generation', 'experience_save')
  .addEdge('experience_save', '__end__')
  .compile();

export const agent = workflow;
```

### 3.3 异常检测 Agent

```typescript
// src/agents/anomaly/detect.ts
import { z } from 'zod';

const anomalyInputSchema = z.object({
  dataset: z.any(),
  metric: z.string(),
  threshold: z.number().default(0.8),
});

export async function detect(state: AnalysisState): Promise<Partial<AnalysisState>> {
  const { dataset, metric } = state;

  // 1. 算法检测
  const algorithms = [
    'zscore',
    'iqr',
    'yoy_change',
    'mom_change',
    'direction',
    'velocity',
    'inflection',
    'seasonality'
  ];

  const algorithmResults = await Promise.all(
    algorithms.map(algo => runAlgorithm(algo, dataset, metric))
  );

  // 2. 信号提取
  const signals = extractSignals(dataset, metric);

  // 3. AI 判断
  const llm = getLLM();
  const aiDecision = await llm.invoke([
    SystemMessage('你是一个金融异常检测专家...'),
    HumanMessage(JSON.stringify({ algorithmResults, signals }))
  ]);

  return {
    anomaly: {
      isAnomaly: aiDecision.isAnomaly,
      score: aiDecision.confidence,
      methods: algorithmResults,
      signal: signals,
      reason: aiDecision.reason
    }
  };
}
```

### 3.4 归因分析 Agent

```typescript
// src/agents/attribution/analyze.ts
export async function analyze(state: AnalysisState): Promise<Partial<AnalysisState>> {
  const { dataset, metric, dimensions, compareType } = state;

  // 1. 维度拆分
  const aggregator = new DynamicAggregator(dataset);
  const dimensionData = aggregator.aggregate(dimensions);

  // 2. 贡献度计算
  const calculator = new ContributionCalculator();
  const contributions = calculator.calculate(dimensionData, compareType);

  // 3. 核心驱动因素排序
  const sorted = contributions.sort((a, b) => Math.abs(b.value - a.baseline) - Math.abs(a.value - a.baseline));

  // 4. AI 业务洞察
  const llm = getLLM();
  const insights = await llm.invoke([
    SystemMessage('你是一个金融归因分析专家...'),
    HumanMessage(JSON.stringify({ contributions: sorted.slice(0, 5) }))
  ]);

  return {
    attribution: {
      contributions,
      totalChange: calculateTotalChange(contributions),
      topDrivers: sorted.filter(c => c.value > c.baseline).slice(0, 3).map(c => c.name),
      topDraggers: sorted.filter(c => c.value < c.baseline).slice(0, 3).map(c => c.name)
    }
  };
}
```

### 3.5 报告生成 Agent

```typescript
// src/agents/reporting/generate.ts
export async function generate(state: AnalysisState): Promise<Partial<AnalysisState>> {
  const { anomaly, attribution, experience } = state;

  const llm = getLLM();

  const report = await llm.invoke([
    SystemMessage(`你是一个专业的金融分析师，生成简洁专业的分析报告。

格式要求：
1. 结论先行
2. 使用业务语言，避免技术术语
3. 提供可行动的建議`),
    HumanMessage(JSON.stringify({
      anomaly,
      attribution,
      experience: experience.matched?.conclusion
    }))
  ]);

  return {
    report: {
      summary: report.summary,
      insights: report.insights,
      suggestions: report.suggestions
    }
  };
}
```

---

## 四、数据模型

### 4.1 核心数据模型

```typescript
// src/models/index.ts

// 单条数据记录
interface Record {
  id: string;
  timestamp: Date;
  dimensions: Record<string, string | number>;
  metrics: Record<string, number>;
}

// 数据集（当前期 + 对比期）
interface Dataset {
  current: Record[];
  baseline: Record[];
  metadata: {
    metric: string;
    dimensions: string[];
    dateRange: { start: Date; end: Date };
  };
}

// 异常检测结果
interface AnomalyResult {
  isAnomaly: boolean;
  score: number; // 0-1
  methods: AnomalyMethod[];
  signal: SignalFeatures;
  reason?: string;
}

interface AnomalyMethod {
  name: string;
  result: boolean;
  value: number;
  threshold: number;
}

interface SignalFeatures {
  direction: 'up' | 'down' | 'stable';
  velocity: number;
  acceleration: number;
  inflection: boolean;
  seasonality: boolean;
}

// 归因分析结果
interface AttributionResult {
  contributions: Contribution[];
  totalChange: number;
  topDrivers: string[];
  topDraggers: string[];
}

interface Contribution {
  dimension: string;
  baseline: number;
  current: number;
  change: number;
  contributionPercent: number;
}

// 经验记录
interface Experience {
  id: string;
  vector: number[]; // 20维特征向量
  features: {
    zscore: number;
    changeRate: number;
    direction: number;
    velocity: number;
    // ... 更多特征
  };
  anomaly: AnomalyResult;
  attribution: AttributionResult;
  conclusion: string;
  confidence: number;
  feedbackCount: number;
  createdAt: Date;
  updatedAt: Date;
}
```

---

## 五、经验系统设计

### 5.1 向量化特征 (20维)

| 维度 | 特征 | 范围/类型 |
|------|------|-----------|
| 1-5 | 统计特征 | zscore归一化、变化率、波动率、季节性系数、周期长度 |
| 6-10 | 信号特征 | 方向编码、速度、加速度、拐点标志、动量 |
| 11-15 | 业务上下文 | 行业编码、月份编码、事件编码、交易日标志、市场状态 |
| 16-20 | 历史模式 | 波动率等级、周期匹配度、趋势强度、异常频率、季节匹配度 |

### 5.2 经验检索流程

```
新分析请求
     │
     ▼
向量特征提取 (20维)
     │
     ▼
向量相似度检索 (余弦相似度 > 0.85)
     │
     ├─ 找到匹配 ──→ 复用结论，更新置信度
     │
     └─ 未找到 ──→ 完整分析流程 → 保存为新经验
```

### 5.3 置信度更新

```typescript
// src/experience/feedback.ts
interface FeedbackUpdate {
  experienceId: string;
  isHelpful: boolean;
  correction?: string;
}

async function updateConfidence(feedback: FeedbackUpdate) {
  const experience = await getExperience(feedback.experienceId);

  if (feedback.isHelpful) {
    experience.confidence = Math.min(1.0, experience.confidence + 0.1);
  } else {
    experience.confidence = Math.max(0.0, experience.confidence - 0.15);

    if (feedback.correction) {
      // 创建修正版经验
      await createCorrectedExperience(experience, feedback.correction);
    }
  }

  experience.feedbackCount += 1;
  await saveExperience(experience);
}
```

---

## 六、API 设计

### 6.1 核心接口

```
POST /api/analyze        # 发起分析
POST /api/feedback       # 用户反馈
GET  /api/experiences    # 查询经验库
GET  /api/experiences/:id # 获取单条经验
POST /api/data/upload    # 上传数据文件
GET  /api/data/sources   # 获取可用数据源
```

详细接口定义见 [API 文档](./api.md)

---

## 七、安全设计

### 7.1 认证授权

- JWT Token 认证
- 角色基础访问控制 (RBAC)
- API 限流 (Rate Limiting)

### 7.2 数据安全

- 文件上传类型校验
- SQL 注入防护 (Prisma 参数化查询)
- XSS 防护 (前端转义)
- CORS 配置

---

## 八、性能优化

### 8.1 后端优化

- **流式处理**：大文件 CSV 分块读取
- **缓存**：热点数据 Redis 缓存
- **异步**：AI 调用异步化，不阻塞主流程
- **连接池**：数据库连接池复用

### 8.2 前端优化

- **懒加载**：路由和组件按需加载
- **虚拟滚动**：长列表虚拟滚动
- **图表优化**：ECharts 按需引入，减少包体积
- **缓存**：Pinia 持久化

---

## 九、监控与日志

### 9.1 日志

- 结构化日志 (Pino)
- 日志级别：error, warn, info, debug
- 日志输出：文件 + 控制台 + ELK

### 9.2 监控

- 健康检查端点 `/health`
- Prometheus 指标暴露
- 关键业务指标埋点

---

## 十、扩展性设计

### 10.1 插件化数据适配器

```typescript
interface DataAdapter {
  readonly name: string;
  read(options: ReadOptions): Promise<Dataset>;
  validate(data: unknown): boolean;
}

// 已有适配器
const adapters: DataAdapter[] = [
  new CsvAdapter(),
  new DatabaseAdapter(),
  new CalcFiAdapter(),
  new BinanceAdapter(),
];
```

### 10.2 可扩展 Agent

```typescript
// 新增 Agent 只需注册
workflow.addNode('custom_agent', customAgent.handler);
workflow.addEdge('attribution_analysis', 'custom_agent');
```

---

## 十一、环境配置

### 11.1 开发环境

```yaml
# .env.development
NODE_ENV=development
PORT=3000
DATABASE_URL=postgresql://localhost:5432/attribution_dev
VECTOR_DB_URL=http://localhost:6333
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
```

### 11.2 生产环境

```yaml
# .env.production
NODE_ENV=production
PORT=3000
DATABASE_URL=postgresql://prod-db:5432/attribution
VECTOR_DB_URL=http://qdrant:6333
LLM_PROVIDER=openai
OPENAI_API_KEY=${OPENAI_API_KEY}
```

---

## 十二、相关文档

- [快速开始](./getting-started.md) - 环境配置和启动
- [API 文档](./api.md) - 接口详细定义
- [部署指南](./deployment.md) - Docker 部署
