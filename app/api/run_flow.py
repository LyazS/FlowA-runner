from typing import List, Dict, Annotated
import asyncio
import uuid
import json
import traceback
from fastapi import APIRouter, Body
from loguru import logger
from fastapi.background import BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import settings
from app.schemas.fanode import FARunStatus
from app.schemas.vfnode import VFlowData, VFNodeFlag
from app.services.FARunner import FARunner
from app.services.FAValidator import FAValidator
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
    FAWorkflow,
    FAWorkflowOperationResponse,
    FAProgressNodeType,
    FAProgressRequest,
    FAWorkflowRunRequest,
    FAWorkflowRunReqType,
    FAWorkflowRunResponse,
)
from app.db.session import get_db_ctxmgr
from app.models.fastore import (
    FAWorkflowModel,
    FAReleasedWorkflowModel,
    FANodeCacheModel,
)
from sqlalchemy import select, update, exc, exists, delete

router = APIRouter()


@router.post("/run")
async def run_flow(run_req: FAWorkflowRunRequest) -> FAWorkflowOperationResponse:
    if settings.DEBUG:
        await asyncio.sleep(1)
    fav = FAValidator()
    flowdata = VFlowData.model_validate(run_req.vflow)

    # 检查工作流是否有效 =============================================
    validate_result = await fav.validate(run_req.wid, flowdata)
    if len(validate_result) > 0:
        return FAWorkflowOperationResponse(
            success=False,
            data=FAWorkflowRunResponse(
                type=FAWorkflowRunReqType.validation,
                validation_errors=validate_result,
            ),
        )

    # 检查是否还在运行 =============================================
    if await ALL_TASKS_MGR.isRunning(run_req.wid):
        return FAWorkflowOperationResponse(
            success=False,
            message="Workflow is running",
            data=FAWorkflowRunResponse(
                type=FAWorkflowRunReqType.isrunning,
            ),
        )

    # 开始运行 =============================================
    await ALL_TASKS_MGR.start_run(run_req.wid, run_req.vflow)
    logger.debug(f"running workflow: {ALL_TASKS_MGR.tasks.keys()}")

    try:
        async with get_db_ctxmgr() as db:
            await db.execute(
                update(FAWorkflowModel)
                .where(FAWorkflowModel.wid == run_req.wid)
                .values(
                    curVFlow=run_req.vflow,
                    lastModified=datetime.now(ZoneInfo("Asia/Shanghai")),
                )
            )
            await db.commit()

    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"update workflow error: {errmsg}")
        return FAWorkflowOperationResponse(
            success=False,
            message=errmsg,
            data=FAWorkflowRunResponse(
                type=FAWorkflowRunReqType.internalerror,
            ),
        )
    return FAWorkflowOperationResponse(
        success=True,
        data=FAWorkflowRunResponse(
            type=FAWorkflowRunReqType.success,
        ),
    )


@router.post("/stop")
async def stop_flow(stop_req: FAWorkflowRunRequest) -> FAWorkflowOperationResponse:
    if await ALL_TASKS_MGR.isRunning(stop_req.wid):
        await ALL_TASKS_MGR.stop(stop_req.wid)
        logger.debug(f"running workflow: {ALL_TASKS_MGR.tasks.keys()}")
        return FAWorkflowOperationResponse(
            success=True,
            message="Workflow stopped",
        )
    else:
        return FAWorkflowOperationResponse(
            success=True,
            message="Not found the Workflow",
        )
    pass


@router.get("/status")
async def get_flow_status(wid: str) -> FAWorkflowOperationResponse:
    if await ALL_TASKS_MGR.isRunning(wid):
        return FAWorkflowOperationResponse(success=True)
    else:
        return FAWorkflowOperationResponse(success=False)
    pass


@router.post("/progress")
async def get_task_progress(prequest_body: Annotated[str, Body()]):
    prequest = FAProgressRequest.model_validate_json(prequest_body)
    task_name = prequest.tid
    logger.debug(f"get_task_progress {task_name}")

    async def event_generator():
        if await ALL_MESSAGES_MGR.has(task_name):
            return
        fetch_nids = []
        try:
            # 第一步，创建消息管理器
            # 推送整体情况
            # 推送剩余情况
            # 在进度完成后，叫前端post获取一次完整结果
            await ALL_MESSAGES_MGR.create(task_name)
            tnames = task_name.split("/")
            if len(tnames) == 2:
                taskid, tasktype = tnames
                logger.debug(f"get progress {taskid} {tasktype}")
            else:
                taskid = tnames[0]
            farunner: FARunner = await ALL_TASKS_MGR.get(taskid)
            if farunner is None:
                raise Exception("Task not found")
            all_sse_data: List[SSEResponseData] = []
            if prequest.node_type == FAProgressNodeType.ALL_TASK_NODE:
                for nid in farunner.nodes.keys():
                    node = farunner.getNode(nid)
                    if node.data.flag & VFNodeFlag.isTask:
                        fetch_nids.append(nid)
                    pass
                pass
            elif prequest.node_type == FAProgressNodeType.SELECTED:
                fetch_nids = prequest.selected_nids
                pass
            for nid in fetch_nids:
                if nid not in farunner.nodes:
                    logger.warning(f"node {nid} not found in task {taskid}")
                    continue
                await farunner.nodes[nid].startReport()
                ndata = await farunner.nodes[nid].getCurData()
                if ndata is None:
                    continue
                sse_data = SSEResponseData(
                    nid=nid,
                    oriid=farunner.nodes[nid].oriid,
                    data=ndata,
                )
                all_sse_data.append(sse_data)
                pass
            ALL_MESSAGES_MGR.put(
                task_name,
                SSEResponse(
                    event=SSEResponseType.batchupdatenode,
                    data=all_sse_data,
                ),
            )
            if farunner.status == FARunStatus.Success:
                ALL_MESSAGES_MGR.put(
                    task_name,
                    SSEResponse(
                        event=SSEResponseType.flowfinish,
                        data=None,
                    ),
                )
            pass
            while True:
                # 第二步,去检查各个未完成任务的进度
                p_msg = await ALL_MESSAGES_MGR.get(task_name)
                # if p_msg is None:
                #     continue
                # if prequest.node_type == FAProgressNodeType.SELECTED:
                #     logger.debug(p_msg.model_dump_json(indent=2))
                yield p_msg.toSSEResponse()
                ALL_MESSAGES_MGR.task_done(task_name)
                if p_msg.event == SSEResponseType.flowfinish:
                    break
                pass

        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(error_msg)
            pass
        finally:
            await ALL_MESSAGES_MGR.remove(task_name)
            for nid in fetch_nids:
                await farunner.nodes[nid].stopReport()
                pass
            logger.info(f"task done {task_name}")
            pass

    return EventSourceResponse(event_generator())
