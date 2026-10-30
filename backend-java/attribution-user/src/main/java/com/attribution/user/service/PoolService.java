package com.attribution.user.service;

import java.util.List;

import com.attribution.common.response.PageResult;
import com.attribution.user.dto.PoolCreateRequest;
import com.attribution.user.dto.PoolMemberMemoRequest;
import com.attribution.user.dto.PoolMembersRequest;
import com.attribution.user.dto.PoolOperationCreateRequest;
import com.attribution.user.dto.PoolQuery;
import com.attribution.user.dto.PoolUpdateRequest;
import com.attribution.user.vo.OperationProgressVO;
import com.attribution.user.vo.PoolAddMembersVO;
import com.attribution.user.vo.PoolDetailVO;
import com.attribution.user.vo.PoolMemberVO;
import com.attribution.user.vo.PoolOperationCreateVO;
import com.attribution.user.vo.PoolOperationVO;
import com.attribution.user.vo.PoolVO;
import com.attribution.user.vo.PoolsBySymbolVO;

/**
 * 自选池服务。
 *
 * <p>接口签名统一使用 DTO（入参）与 VO（出参），不暴露 PO 与裸 Map。
 */
public interface PoolService {
    PoolVO create(PoolCreateRequest request);

    PageResult<PoolVO> list(PoolQuery query);

    PoolDetailVO one(int id);

    PoolVO patch(int id, PoolUpdateRequest request);

    void delete(int id);

    PoolAddMembersVO addMembers(int id, PoolMembersRequest request);

    int removeMembers(int id, PoolMembersRequest request);

    PageResult<PoolMemberVO> members(int id, int page, int pageSize);

    PoolMemberVO memo(int id, String symbol, PoolMemberMemoRequest request);

    PoolsBySymbolVO bySymbol(String symbol);

    PoolOperationCreateVO createOp(int id, PoolOperationCreateRequest request);

    PageResult<PoolOperationVO> ops(int id, int page, int pageSize);

    PoolOperationVO opOne(int id);

    OperationProgressVO opProgress(int id);

    void cancel(int id);
}
