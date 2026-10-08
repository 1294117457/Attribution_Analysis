"""数据备份 API 路由（业务模块：backup/）

URL：/api/v1/backups/...

路由顺序：静态路径在前，/{rid} 通配在后（避免 /restore 被 /{rid} 吃掉）
"""

from __future__ import annotations

from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from application.service.backup_app_service import BackupAppService
from infrastructure.adapter.backup.exceptions import (
    BackupError,
    BackupTaskRunningError,
    InvalidBackupFileError,
    PathSecurityError,
)
from infrastructure.config.di import get_backup_app_service
from route.api import _response as R
from route.api.v1.deps_auth import get_current_user_id
from route.dto.backup.request.create_backup import CreateBackupRequest
from route.dto.backup.request.restore import RestoreRequest
from route.dto.backup.request.update_config import UpdateConfigRequest
from route.dto.backup.response.backup import (
    BackupListResponse,
    BackupRecordDTO,
    RestoreListResponse,
    RestoreRecordDTO,
)
from route.dto.backup.response.config import BackupConfigDTO, UploadBackupResponse
from route.dto.backup.response.table import TableInfoDTO

router = APIRouter(prefix="/backups", tags=["数据备份"])


# ═════════════════════════════════════════════════════
#  静态路径：配置 / 表元信息 / 列表 / 恢复 / 上传
#  （必须放在 /{rid} 之前，否则会被 /{rid} 吃掉）
# ═════════════════════════════════════════════════════
@router.get("/config", summary="获取备份配置")
async def get_config(
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    cfg = await service.get_backup_config()
    return R.ok(cfg)


@router.put("/config", summary="更新备份配置")
async def update_config(
    req: UpdateConfigRequest,
    user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    await service.update_backup_config(req, user_id)
    return R.ok()


@router.get("/_tables", summary="列出可备份的表")
async def list_tables(
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    tables = await service.list_tables()
    return R.ok(tables)


@router.post(
    "",
    summary="创建备份任务（异步）",
    status_code=status.HTTP_201_CREATED,
)
async def create_backup(
    req: CreateBackupRequest,
    user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    record_id = await service.create_backup(req, user_id)
    return R.created({"id": record_id})


@router.get("", summary="备份列表")
async def list_backups(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    items, total = await service.list_backups(
        page=page, page_size=page_size, status=status
    )
    return R.ok(
        {
            "items": [BackupRecordDTO(**i).model_dump(mode="json") for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


# ═════════════════════════════════════════════════════
#  恢复路由（在 /{rid} 之前）
# ═════════════════════════════════════════════════════
@router.post(
    "/restore",
    summary="创建恢复任务（异步）",
    status_code=status.HTTP_201_CREATED,
)
async def create_restore(
    req: RestoreRequest,
    user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    record_id = await service.create_restore(req, user_id)
    return R.created({"id": record_id})


@router.get("/restore", summary="恢复列表")
async def list_restores(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    items, total = await service.list_restores(page=page, page_size=page_size)
    return R.ok(
        {
            "items": [RestoreRecordDTO(**i).model_dump(mode="json") for i in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/restore/{rid}", summary="单条恢复详情")
async def get_restore(
    rid: int = Path(..., description="恢复记录 ID"),
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    record = await service.get_restore(rid)
    if not record:
        raise HTTPException(status_code=404, detail="恢复记录不存在")
    return R.ok(RestoreRecordDTO(**record).model_dump(mode="json"))


@router.post("/upload", summary="上传 .sql 备份文件")
async def upload_backup(
    file: UploadFile = File(..., description=".sql 文件"),
    user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")
    if not file.filename.endswith(".sql"):
        raise HTTPException(status_code=400, detail="只支持 .sql 文件")

    content = await file.read()
    result = await service.upload_backup_file(content, file.filename, user_id)
    return R.ok(result)


# ═════════════════════════════════════════════════════
#  /{rid} 通配路由（必须放最后，避免吃掉 /restore 等）
# ═════════════════════════════════════════════════════
@router.get("/{rid}", summary="单条备份详情")
async def get_backup(
    rid: int = Path(..., description="备份记录 ID"),
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    record = await service.get_backup(rid)
    if not record:
        raise HTTPException(status_code=404, detail="备份不存在")
    return R.ok(BackupRecordDTO(**record).model_dump(mode="json"))


@router.get("/{rid}/download", summary="下载 .sql")
async def download_backup(
    rid: int = Path(..., description="备份记录 ID"),
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    file_path = await service.get_download_path(rid)
    if not file_path.exists():
        raise HTTPException(status_code=410, detail="文件已丢失")
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/sql",
    )


@router.delete("/{rid}", summary="删除备份")
async def delete_backup(
    rid: int = Path(..., description="备份记录 ID"),
    _user_id: int = Depends(get_current_user_id),
    service: BackupAppService = Depends(get_backup_app_service),
):
    await service.delete_backup(rid)
    return R.no_content("备份已删除")
