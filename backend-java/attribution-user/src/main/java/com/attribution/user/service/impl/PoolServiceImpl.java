package com.attribution.user.service.impl;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.attribution.collector.client.CollectorService;
import com.attribution.common.exception.BusinessException;
import com.attribution.common.mybatis.TopN;
import com.attribution.common.response.PageResult;
import com.attribution.market.service.StockInfoService;
import com.attribution.market.vo.StockBriefVO;
import com.attribution.user.converter.PoolConverter;
import com.attribution.user.dto.PoolCreateRequest;
import com.attribution.user.dto.PoolMemberMemoRequest;
import com.attribution.user.dto.PoolMembersRequest;
import com.attribution.user.dto.PoolOperationCreateRequest;
import com.attribution.user.dto.PoolQuery;
import com.attribution.user.dto.PoolUpdateRequest;
import com.attribution.user.entity.PoolMemberPO;
import com.attribution.user.entity.PoolOperationPO;
import com.attribution.user.entity.StockPoolPO;
import com.attribution.user.mapper.PoolMemberMapper;
import com.attribution.user.mapper.PoolOperationMapper;
import com.attribution.user.mapper.StockPoolMapper;
import com.attribution.user.service.PoolService;
import com.attribution.user.vo.OperationProgressVO;
import com.attribution.user.vo.PoolAddMembersVO;
import com.attribution.user.vo.PoolDetailVO;
import com.attribution.user.vo.PoolMemberVO;
import com.attribution.user.vo.PoolOperationCreateVO;
import com.attribution.user.vo.PoolOperationVO;
import com.attribution.user.vo.PoolVO;
import com.attribution.user.vo.PoolsBySymbolVO;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.ObjectMapper;

@Service
public class PoolServiceImpl implements PoolService {
    private final StockPoolMapper stockPoolMapper;
    private final PoolMemberMapper poolMemberMapper;
    private final PoolOperationMapper poolOperationMapper;

    /** 跨模块调用其他模块的 Service，不直接注入其 Mapper（见 docs/规范文档/纵向分层规范/Service层规范.md §2.4） */
    private final StockInfoService stockInfoService;

    private final CollectorService collectorService;

    /**
     * Spring 管理的 ObjectMapper（复用全局 Jackson 配置）。
     *
     * <p>序列化给池操作记录用，反序列化由 {@link PoolConverter} 完成——
     * 两者必须用**同一个**实例，否则写进去的格式和读出来的格式可能不一致。
     */
    private final ObjectMapper objectMapper;

    /** 采集任务的执行器，由 Spring 管理生命周期 */
    private final java.util.concurrent.Executor executor;

    public PoolServiceImpl(
            StockPoolMapper stockPoolMapper,
            PoolMemberMapper poolMemberMapper,
            PoolOperationMapper poolOperationMapper,
            StockInfoService stockInfoService,
            CollectorService collectorService,
            ObjectMapper objectMapper,
            @Qualifier("poolTaskExecutor") java.util.concurrent.Executor executor) {
        this.stockPoolMapper = stockPoolMapper;
        this.poolMemberMapper = poolMemberMapper;
        this.poolOperationMapper = poolOperationMapper;
        this.stockInfoService = stockInfoService;
        this.collectorService = collectorService;
        this.objectMapper = objectMapper;
        this.executor = executor;
    }

    /** 判断「已有进行中操作」时回看的最近操作条数 */
    private static final int RECENT_OPERATION_LIMIT = 5;

    // ── 内部查询 ─────────────────────────────────────────────

    /**
     * 批量统计各池成员数（一次查询替代逐池 count）。
     *
     * @return poolId → 成员数
     */
    private Map<Integer, Long> memberCounts(List<Integer> poolIds) {
        Map<Integer, Long> counts = new HashMap<>();
        if (poolIds == null || poolIds.isEmpty()) return counts;
        for (PoolMemberMapper.PoolMemberCountRow row : poolMemberMapper.selectMemberCounts(poolIds))
            counts.put(row.getPoolId(), row.getMemberCount());
        return counts;
    }

    private long countMembers(int poolId) {
        return poolMemberMapper.selectCount(
                new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getPoolId, poolId));
    }

    /** 批量取股票基础信息（symbol → name/industry/market/exchange），跨模块走 Service。 */
    private Map<String, StockBriefVO> stockBrief(List<String> symbols) {
        return stockInfoService.briefs(symbols);
    }

    private StockPoolPO requirePool(int poolId) {
        StockPoolPO pool = stockPoolMapper.selectById(poolId);
        if (pool == null) throw new BusinessException(404, "池不存在");
        return pool;
    }

    // ── 池管理 ───────────────────────────────────────────────

    @Override
    public PoolVO create(PoolCreateRequest request) {
        StockPoolPO pool = new StockPoolPO();
        pool.setName(request.getName() == null || request.getName().isBlank() ? "默认池" : request.getName().trim());
        pool.setDescription(request.getDescription());
        pool.setPoolType(request.getPoolType() == null ? "custom" : request.getPoolType());
        pool.setColor(request.getColor());
        pool.setIcon(request.getIcon());
        pool.setIsArchived(false);
        pool.setIsDefault(false);
        pool.setSortOrder(0);
        stockPoolMapper.insert(pool);
        return PoolConverter.toVO(pool, 0);
    }

    @Override
    public PageResult<PoolVO> list(PoolQuery query) {
        var wrapper = new LambdaQueryWrapper<StockPoolPO>();
        if (!query.isIncludeArchived()) wrapper.eq(StockPoolPO::getIsArchived, false);
        // count 查询不能带 orderBy（PostgreSQL: column must appear in GROUP BY），
        // 所以先统计总数，再加排序
        long total = stockPoolMapper.selectCount(wrapper);
        wrapper.orderByAsc(StockPoolPO::getId);
        var pageParam = new Page<StockPoolPO>(query.getPage(), query.getPageSize());
        List<StockPoolPO> pools = stockPoolMapper.selectPage(pageParam, wrapper).getRecords();

        // 批量统计成员数，避免逐池 count
        List<Integer> poolIds = pools.stream().map(StockPoolPO::getId).toList();
        Map<Integer, Long> counts = memberCounts(poolIds);

        List<PoolVO> list = new ArrayList<>();
        for (StockPoolPO pool : pools)
            list.add(PoolConverter.toVO(pool, counts.getOrDefault(pool.getId(), 0L)));
        return PageResult.of(total, list, query.getPage(), query.getPageSize());
    }

    @Override
    public PoolDetailVO one(int id) {
        StockPoolPO pool = requirePool(id);
        List<PoolMemberPO> members =
                poolMemberMapper.selectList(
                        new LambdaQueryWrapper<PoolMemberPO>()
                                .eq(PoolMemberPO::getPoolId, id)
                                .orderByAsc(PoolMemberPO::getSymbol));
        List<String> symbols = members.stream().map(PoolMemberPO::getSymbol).toList();
        Map<String, StockBriefVO> briefBySymbol = stockBrief(symbols);
        List<PoolMemberVO> memberVOs = new ArrayList<>();
        for (PoolMemberPO member : members) memberVOs.add(PoolConverter.toVO(member, briefBySymbol));

        PoolDetailVO detailVO = new PoolDetailVO();
        StockPoolPO copy = pool;
        PoolVO base = PoolConverter.toVO(copy, members.size());
        if (base != null) {
            detailVO.setId(base.getId());
            detailVO.setName(base.getName());
            detailVO.setPoolType(base.getPoolType());
            detailVO.setDescription(base.getDescription());
            detailVO.setColor(base.getColor());
            detailVO.setIcon(base.getIcon());
            detailVO.setSortOrder(base.getSortOrder());
            detailVO.setIsDefault(base.getIsDefault());
            detailVO.setIsArchived(base.getIsArchived());
            detailVO.setMemberCount(base.getMemberCount());
            detailVO.setCreatedAt(base.getCreatedAt());
            detailVO.setUpdatedAt(base.getUpdatedAt());
        }
        detailVO.setMembers(memberVOs);
        return detailVO;
    }

    @Override
    public PoolVO patch(int id, PoolUpdateRequest request) {
        StockPoolPO pool = requirePool(id);
        if (request.getName() != null) pool.setName(request.getName());
        if (request.getDescription() != null) pool.setDescription(request.getDescription());
        if (request.getColor() != null) pool.setColor(request.getColor());
        if (request.getIcon() != null) pool.setIcon(request.getIcon());
        if (request.getSortOrder() != null) pool.setSortOrder(request.getSortOrder());
        stockPoolMapper.updateById(pool);
        return PoolConverter.toVO(pool, countMembers(id));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void delete(int id) {
        StockPoolPO pool = requirePool(id);
        if (Boolean.TRUE.equals(pool.getIsDefault())) throw new BusinessException(400, "默认池不能删除");
        poolMemberMapper.delete(new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getPoolId, id));
        stockPoolMapper.deleteById(id);
    }

    // ── 成员管理 ─────────────────────────────────────────────

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PoolAddMembersVO addMembers(int id, PoolMembersRequest request) {
        requirePool(id);
        List<String> symbols = request.getSymbols() == null ? List.of() : request.getSymbols();
        boolean validate = !Boolean.FALSE.equals(request.getValidateExists());

        List<String> added = new ArrayList<>();
        List<String> skipped = new ArrayList<>();
        if (symbols.isEmpty()) {
            PoolAddMembersVO empty = new PoolAddMembersVO();
            empty.setPoolId(id);
            empty.setAdded(added);
            empty.setSkipped(skipped);
            empty.setTotalAdded(0);
            empty.setTotalSkipped(0);
            return empty;
        }

        // 一次性查出已存在的成员，避免逐个 selectCount（N+1）
        Set<String> existing = new java.util.HashSet<>(poolMemberMapper.selectExistingSymbols(id, symbols));
        // 一次性校验股票是否存在，避免逐个查询（N+1）
        Set<String> validSymbols = null;
        if (validate) validSymbols = stockInfoService.briefs(symbols).keySet();

        for (String symbol : symbols) {
            if (validSymbols != null && !validSymbols.contains(symbol)) {
                skipped.add(symbol);
                continue;
            }
            if (existing.contains(symbol)) {
                skipped.add(symbol);
                continue;
            }
            PoolMemberPO member = new PoolMemberPO();
            member.setPoolId(id);
            member.setSymbol(symbol);
            member.setSortOrder(0);
            member.setAddedAt(LocalDateTime.now());
            poolMemberMapper.insert(member);
            added.add(symbol);
        }

        PoolAddMembersVO resultVO = new PoolAddMembersVO();
        resultVO.setPoolId(id);
        resultVO.setAdded(added);
        resultVO.setSkipped(skipped);
        resultVO.setTotalAdded(added.size());
        resultVO.setTotalSkipped(skipped.size());
        return resultVO;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int removeMembers(int id, PoolMembersRequest request) {
        List<String> symbols = request.getSymbols() == null ? List.of() : request.getSymbols();
        if (symbols.isEmpty()) return 0;
        // 一次删除全部待移除成员，替代逐个 delete
        return poolMemberMapper.delete(
                new LambdaQueryWrapper<PoolMemberPO>()
                        .eq(PoolMemberPO::getPoolId, id)
                        .in(PoolMemberPO::getSymbol, symbols));
    }

    @Override
    public PageResult<PoolMemberVO> members(int id, int page, int pageSize) {
        requirePool(id);
        var memberWrapper = new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getPoolId, id);
        // count 查询不能带 orderBy（PostgreSQL: column must appear in GROUP BY）
        long total = poolMemberMapper.selectCount(memberWrapper);
        memberWrapper.orderByAsc(PoolMemberPO::getSymbol);
        var pageParam = new Page<PoolMemberPO>(page, pageSize);
        List<PoolMemberPO> members = poolMemberMapper.selectPage(pageParam, memberWrapper).getRecords();
        Map<String, StockBriefVO> briefBySymbol =
                stockBrief(members.stream().map(PoolMemberPO::getSymbol).toList());
        List<PoolMemberVO> list = new ArrayList<>();
        for (PoolMemberPO member : members) list.add(PoolConverter.toVO(member, briefBySymbol));
        return PageResult.of(total, list, page, pageSize);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PoolMemberVO memo(int id, String symbol, PoolMemberMemoRequest request) {
        List<PoolMemberPO> existing =
                poolMemberMapper.selectList(
                        new LambdaQueryWrapper<PoolMemberPO>()
                                .eq(PoolMemberPO::getPoolId, id)
                                .eq(PoolMemberPO::getSymbol, symbol));
        if (existing.isEmpty()) throw new BusinessException(404, "成员不存在");
        String memoValue = request.getMemo() == null ? "" : request.getMemo();
        poolMemberMapper.delete(
                new LambdaQueryWrapper<PoolMemberPO>()
                        .eq(PoolMemberPO::getPoolId, id)
                        .eq(PoolMemberPO::getSymbol, symbol));
        PoolMemberPO member = existing.get(0);
        member.setMemo(memoValue);
        poolMemberMapper.insert(member);
        return PoolConverter.toVO(member, stockBrief(List.of(symbol)));
    }

    @Override
    public PoolsBySymbolVO bySymbol(String symbol) {
        List<PoolMemberPO> memberships =
                poolMemberMapper.selectList(
                        new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getSymbol, symbol));
        // 批量取池，避免逐个 selectById（N+1）
        List<Integer> poolIds = memberships.stream().map(PoolMemberPO::getPoolId).distinct().toList();
        List<StockPoolPO> pools =
                poolIds.isEmpty() ? List.of() : stockPoolMapper.selectBatchIds(poolIds);
        Map<Integer, Long> counts = memberCounts(poolIds);

        List<PoolVO> poolVOs = new ArrayList<>();
        for (StockPoolPO pool : pools)
            poolVOs.add(PoolConverter.toVO(pool, counts.getOrDefault(pool.getId(), 0L)));

        PoolsBySymbolVO resultVO = new PoolsBySymbolVO();
        resultVO.setSymbol(symbol);
        resultVO.setPools(poolVOs);
        resultVO.setTotal(poolVOs.size());
        return resultVO;
    }

    // ── 池级操作 ─────────────────────────────────────────────

    @Override
    public PoolOperationCreateVO createOp(int id, PoolOperationCreateRequest request) {
        requirePool(id);
        var recentWrapper =
                new LambdaQueryWrapper<PoolOperationPO>()
                        .eq(PoolOperationPO::getPoolId, id)
                        .orderByDesc(PoolOperationPO::getId);
        List<PoolOperationPO> recent = TopN.query(poolOperationMapper, recentWrapper, RECENT_OPERATION_LIMIT);
        for (PoolOperationPO operation : recent)
            if ("pending".equals(operation.getStatus()) || "running".equals(operation.getStatus()))
                throw new BusinessException(409, "已有进行中的操作");

        int days = request.getDays() == null ? 365 : request.getDays();
        String operationType =
                request.getOperationType() == null ? "kline_collect" : request.getOperationType();
        List<String> symbols =
                poolMemberMapper.selectList(
                                new LambdaQueryWrapper<PoolMemberPO>().eq(PoolMemberPO::getPoolId, id))
                        .stream()
                        .map(PoolMemberPO::getSymbol)
                        .toList();

        PoolOperationCreateVO resultVO = new PoolOperationCreateVO();
        resultVO.setPoolId(id);
        resultVO.setOperationType(operationType);
        if (symbols.isEmpty()) {
            resultVO.setOperationId(0);
            resultVO.setStatus("skipped");
            resultVO.setTotal(0);
            resultVO.setMessage("池内没有成员");
            return resultVO;
        }

        PoolOperationPO operation = new PoolOperationPO();
        operation.setPoolId(id);
        operation.setOperationType(operationType);
        operation.setStatus("pending");
        operation.setParams(writeJson(Map.of("days", days), "{\"days\":" + days + "}"));
        operation.setProgress(
                writeJson(
                        Map.of("done", 0, "total", symbols.size(), "failed", 0),
                        "{\"done\":0,\"total\":" + symbols.size() + ",\"failed\":0}"));
        operation.setCreatedAt(LocalDateTime.now());
        poolOperationMapper.insert(operation);

        int operationId = operation.getId();
        final int finalDays = days;
        final List<String> finalSymbols = new ArrayList<>(symbols);
        // 异步任务在事务之外执行：远程调用不放进 @Transactional 方法，避免长时间占用数据库连接
        executor.execute(() -> runCollectOperation(operationId, finalSymbols, finalDays));

        resultVO.setOperationId(operationId);
        resultVO.setStatus("pending");
        resultVO.setTotal(symbols.size());
        resultVO.setMessage("操作已派发，共 " + symbols.size() + " 只股票");
        return resultVO;
    }

    /**
     * 执行采集任务并回写操作状态（转后台任务：建任务立即返回 task_id，不同步等待终态）。
     *
     * <p>独立于调用方事务：远程调用可能耗时数秒，放在事务内会长期占用数据库连接。
     */
    private void runCollectOperation(int operationId, List<String> symbols, int days) {
        try {
            PoolOperationPO current = poolOperationMapper.selectById(operationId);
            if (current == null) return;
            current.setStatus("running");
            current.setStartedAt(LocalDateTime.now());
            poolOperationMapper.updateById(current);

            Map<String, Object> taskResult =
                    collectorService.createTask(
                            "tech",
                            "daily_kline",
                            Map.of("symbols", symbols, "days", days),
                            "condition");

            current = poolOperationMapper.selectById(operationId);
            if (current == null) return;
            current.setStatus("running");
            current.setResultSummary(writeJson(taskResult, String.valueOf(taskResult)));
            current.setProgress(
                    writeJson(
                            Map.of("done", 0, "total", symbols.size(), "failed", 0,
                                    "task_id", taskResult.getOrDefault("task_id", "")),
                            "{\"done\":0,\"total\":" + symbols.size() + ",\"failed\":0}"));
            current.setFinishedAt(null);
            poolOperationMapper.updateById(current);
        } catch (Exception e) {
            try {
                PoolOperationPO current = poolOperationMapper.selectById(operationId);
                if (current == null) return;
                current.setStatus("failed");
                current.setErrorMessage(e.getMessage());
                current.setFinishedAt(LocalDateTime.now());
                poolOperationMapper.updateById(current);
            } catch (Exception ignored) {
                // 状态回写失败：记录日志即可，任务本身已失败
            }
        }
    }

    /** 序列化为 JSON，失败时回退到默认文本 */
    private String writeJson(Object value, String fallback) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            return fallback;
        }
    }

    @Override
    public PageResult<PoolOperationVO> ops(int id, int page, int pageSize) {
        var wrapper = new LambdaQueryWrapper<PoolOperationPO>().eq(PoolOperationPO::getPoolId, id);
        // count 查询不能带 orderBy（PostgreSQL: column must appear in GROUP BY）
        long total = poolOperationMapper.selectCount(wrapper);
        wrapper.orderByDesc(PoolOperationPO::getId);
        var pageParam = new Page<PoolOperationPO>(page, pageSize);
        List<PoolOperationVO> list =
                PoolConverter.toOperationVOList(
                        poolOperationMapper.selectPage(pageParam, wrapper).getRecords(), objectMapper);
        return PageResult.of(total, list, page, pageSize);
    }

    @Override
    public PoolOperationVO opOne(int id) {
        PoolOperationPO operation = poolOperationMapper.selectById(id);
        if (operation == null) throw new BusinessException(404, "操作不存在");
        return PoolConverter.toVO(operation, objectMapper);
    }

    @Override
    public OperationProgressVO opProgress(int id) {
        PoolOperationPO operation = poolOperationMapper.selectById(id);
        if (operation == null) throw new BusinessException(404, "操作不存在");
        return PoolConverter.toProgress(operation.getProgress(), objectMapper);
    }

    @Override
    public void cancel(int id) {
        PoolOperationPO operation = poolOperationMapper.selectById(id);
        if (operation == null) throw new BusinessException(404, "操作不存在");
        if (!"pending".equals(operation.getStatus()) && !"running".equals(operation.getStatus()))
            throw new BusinessException(400, "该操作无法取消");
        operation.setStatus("cancelled");
        operation.setFinishedAt(LocalDateTime.now());
        poolOperationMapper.updateById(operation);
    }
}
