# 02 · 统一分页响应（PageVO）

> 本文档定义系统中所有**列表查询接口**的返回结构。  
> 与 `03-api-response.md` 配合使用：`PageVO` 是 `data` 字段的形态之一。

---

## 1. 设计目标

| 目标              | 描述                                       |
| ----------------- | ------------------------------------------ |
| 字段稳定          | 前端无须关心分页字段命名变更                |
| 兼容未来          | 后续可平滑扩展 `hasNext` / `totalPages` 等字段 |
| 减少冗余          | 一次返回包含"总数 / 当前页 / 页大小 / 数据" |
| 与现有 `code/data/msg` 兼容 | 见 `03-api-response.md`，分页是 data 的形态 |

---

## 2. 数据结构

### 2.1 JSON 形态

```jsonc
{
  "code": 0,
  "data": {
    "total": 123,           // 总记录数（数据库实际命中条数）
    "page": 1,              // 当前页（从 1 开始）
    "pageSize": 20,         // 页大小
    "dataList": [ ... ]     // 当前页数据（数组）
  },
  "msg": "ok"
}
```

### 2.2 字段定义

| 字段         | 类型       | 是否可缺省 | 含义                                    |
| ------------ | ---------- | ---------- | --------------------------------------- |
| `total`      | `long`     | 否         | 总记录数（≥ `dataList.length`）          |
| `page`       | `int`      | 否         | 当前页号（**从 1 开始**）                |
| `pageSize`   | `int`      | 否         | 页大小（请求里传入的值，原样回传）       |
| `dataList`   | `array<T>` | 否         | 当前页数据（空列表返回 `[]`，不返回 null） |

> 🔑 **`dataList` 不返回 null**。  
> 即便查不到任何数据，也是 `"dataList": []`。这避免了前端做 `null` 判断。

### 2.3 字段命名：为什么是 `dataList` 而非 `items` / `rows`

- `items` 简洁，但与业务名词易冲突（如 `PoolItem`）
- `rows` 是 SQL 思维残留，暴露内部实现
- **`dataList` 显式表达"数据列表"语义，前端键名固定，团队无须讨论**

---

## 3. Java 类型定义（建议）

### 3.1 通用泛型类

```java
package com.attribution.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Collections;
import java.util.List;

@Data
@Schema(description = "统一分页响应结构")
public class PageVO<T> {

    @Schema(description = "总记录数")
    private long total;

    @Schema(description = "当前页号（从 1 开始）")
    private int page;

    @Schema(description = "页大小")
    private int pageSize;

    @Schema(description = "当前页数据列表")
    private List<T> dataList;

    public static <T> PageVO<T> empty(int page, int pageSize) {
        PageVO<T> vo = new PageVO<>();
        vo.total = 0L;
        vo.page = page;
        vo.pageSize = pageSize;
        vo.dataList = Collections.emptyList();
        return vo;
    }

    public static <T> PageVO<T> of(long total, int page, int pageSize, List<T> dataList) {
        PageVO<T> vo = new PageVO<>();
        vo.total = total;
        vo.page = page;
        vo.pageSize = pageSize;
        vo.dataList = dataList == null ? Collections.emptyList() : dataList;
        return vo;
    }
}
```

### 3.2 请求基类（PageQuery）

```java
package com.attribution.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "分页请求基类")
public class PageQuery {

    @Schema(description = "页号（从 1 开始）", defaultValue = "1")
    private int page = 1;

    @Schema(description = "页大小", defaultValue = "20")
    private int pageSize = 20;

    public int safePage() {
        return Math.max(1, page);
    }

    public int safePageSize() {
        return pageSize <= 0 ? 20 : Math.min(pageSize, 500);
    }
}
```

---

## 4. Query 参数约定

### 4.1 必填项

| 参数     | 类型 | 默认值 | 取值范围                  |
| -------- | ---- | ------ | ------------------------- |
| `page`   | int  | `1`    | `[1, +∞)`                 |
| `pageSize` | int | `20`   | `[1, 500]`（**上限 500**） |

### 4.2 缺省处理

- 缺省 `page` → 当作 `1` 处理
- 缺省 `pageSize` → 当作 `20` 处理
- `pageSize > 500` → 截断为 `500`，避免一次查询返回过多数据打垮服务
- `page < 1` → 当作 `1`
- `pageSize < 1` → 当作 `20`

### 4.3 排序参数（可选，非强制）

```jsonc
{
  "sortBy": "marketCap",     // 字段名
  "sortDir": "desc"          // asc / desc
}
```

> 如果业务接口不需要排序，可不暴露这两个参数。

---

## 5. Controller 写法（Spring）

### 5.1 标准写法

```java
@GetMapping("/list")
public ApiResponse<PageVO<StockInfoVO>> list(
        @Valid StockListQuery query,    // 继承 PageQuery
        @RequestParam(required = false) String industry
) {
    return ApiResponse.ok(stockService.list(query));
}
```

### 5.2 Service 返回

```java
public PageVO<StockInfoVO> list(StockListQuery query) {
    long total = repo.countByIndustry(query.getIndustry());
    List<StockInfoVO> data = repo.findPage(
        query.getIndustry(),
        query.safePage(),
        query.safePageSize()
    );
    return PageVO.of(total, query.safePage(), query.safePageSize(), data);
}
```

### 5.3 空结果写法

```java
if (data.isEmpty()) {
    return PageVO.empty(query.safePage(), query.safePageSize());
}
```

> ⚠️ **不要** 在空结果时返回 null 或抛业务异常。返回 `dataList: []` 让前端正常渲染空状态。

---

## 6. 完整响应示例

### 6.1 正常有数据

```jsonc
{
  "code": 0,
  "data": {
    "total": 153,
    "page": 1,
    "pageSize": 20,
    "dataList": [
      { "symbol": "000001.SZ", "name": "平安银行" },
      { "symbol": "000002.SZ", "name": "万科A" }
    ]
  },
  "msg": "ok"
}
```

### 6.2 空数据

```jsonc
{
  "code": 0,
  "data": {
    "total": 0,
    "page": 1,
    "pageSize": 20,
    "dataList": []
  },
  "msg": "ok"
}
```

### 6.3 末页（不足一页）

```jsonc
{
  "code": 0,
  "data": {
    "total": 153,
    "page": 8,
    "pageSize": 20,
    "dataList": [ ... 13 条 ... ]
  },
  "msg": "ok"
}
```

---

## 7. 边界与异常

| 场景                          | 处理方式                                    |
| ----------------------------- | ------------------------------------------- |
| `page` 超过 `total` 对应的页  | 正常返回，`dataList: []`，**不报错**        |
| `pageSize` 超过上限           | 截断为 500                                  |
| 后端 SQL 异常                 | 返回错误响应（见 `03-api-response.md`）    |
| 数据量极大（>10w 行）         | 强制走 ES / ClickHouse（架构层面解决）      |

---

## 8. 不适用 PageVO 的场景

以下接口**不**使用 PageVO，而是返回普通列表：

| 场景               | 原因                                       |
| ------------------ | ------------------------------------------ |
| 下拉框 / 选项列表  | 数据固定，无需分页                          |
| 全量导出           | 应使用异步导出 + 任务模式                   |
| 单资源查询         | 本身就是 `ApiResponse<T>`，不是列表        |

---

## 9. 评审 checklist

- [ ] 字段命名（`total` / `page` / `pageSize` / `dataList`）接受
- [ ] `dataList` 永不返回 null 这条规则接受
- [ ] `pageSize` 上限 500 接受
- [ ] `page` 从 1 开始接受（与数据库 0-based 区分）
- [ ] 排序参数（`sortBy` / `sortDir`）可选暴露这条规则接受
- [ ] 空结果返回 `dataList: []` 而不是抛业务异常这条规则接受
- [ ] 不适用 PageVO 的场景列表（第 8 节）覆盖完整

---

## 10. 变更记录

| 版本 | 日期       | 变更人 | 变更内容                       |
| ---- | ---------- | ------ | ------------------------------ |
| v0.2 | 2026-09-25 | -      | 响应示例去掉 `traceId` 字段    |
| v0.1 | 2026-09-25 | -      | 初稿，待评审                   |
