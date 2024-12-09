from typing import List, Dict
import asyncio
import uuid
import traceback
from fastapi import APIRouter
from loguru import logger
from fastapi.background import BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from app.core.config import settings
from app.schemas.fanode import FARunnerStatus
from app.schemas.vfnode import VFlowData
from app.services.FARunner import FARunner
from app.services.FAValidator import FAValidator
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR
from app.schemas.farequest import (
    FARunRequest,
    FARunResponse,
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
    FAWorkflow,
)

router = APIRouter()


@router.post("/run")
async def run_flow(
    fa_req: FAWorkflow,
    background_tasks: BackgroundTasks,
) -> FARunResponse:
    if settings.DEBUG:
        await asyncio.sleep(1)
    taskid = str(uuid.uuid4()).replace("-", "")
    if fa_req.name is None:
        fa_req.name = taskid
    fav = FAValidator()
    flowdata = VFlowData.model_validate(fa_req.vflow)
    validate_result = await fav.validate(taskid, flowdata)
    if len(validate_result) > 0:
        return FARunResponse(
            success=False,
            tid=None,
            validation_errors=validate_result,
        )
    # 通过检查 =============================================
    await ALL_TASKS_MGR.create(taskid)
    background_tasks.add_task(ALL_TASKS_MGR.run, taskid, fa_req)
    return FARunResponse(success=True, tid=taskid)


@router.get("/progress")
async def get_task_progress(taskid: str):
    logger.debug("get_task_progress", taskid)

    async def event_generator():
        try:
            # 第一步，创建消息管理器
            # 推送整体情况
            # 推送剩余情况
            # 在进度完成后，叫前端post获取一次完整结果
            await ALL_MESSAGES_MGR.create(taskid)
            farunner: FARunner = await ALL_TASKS_MGR.get(taskid)
            if farunner is None:
                raise Exception("Task not found")
            all_sse_data: List[SSEResponseData] = []
            for nid in farunner.nodes.keys():
                ndata = farunner.nodes[nid].getCurData()
                if ndata is None:
                    continue
                sse_data = SSEResponseData(
                    nid=nid,
                    oriid=farunner.nodes[nid].oriid,
                    data=ndata,
                )
                all_sse_data.append(sse_data)
            ALL_MESSAGES_MGR.put(
                taskid,
                SSEResponse(
                    event=SSEResponseType.batchupdatenode,
                    data=all_sse_data,
                ),
            )
            if farunner.status == FARunnerStatus.Success:
                ALL_MESSAGES_MGR.put(
                    taskid,
                    SSEResponse(
                        event=SSEResponseType.flowfinish,
                        data=None,
                    ),
                )
            pass
            while True:
                # 第二步,去检查各个未完成任务的进度
                p_msg = await ALL_MESSAGES_MGR.get(taskid)
                # if p_msg is None:
                #     continue
                # logger.debug(p_msg.model_dump_json(indent=2))
                yield p_msg.toSSEResponse()
                ALL_MESSAGES_MGR.task_done(taskid)
                if p_msg.event == SSEResponseType.flowfinish:
                    break
                pass

        except Exception as e:
            error_msg = traceback.format_exc()
            logger.error(error_msg)
            pass
        finally:
            await ALL_MESSAGES_MGR.remove(taskid)
            logger.info("task done", taskid)
            pass

    return EventSourceResponse(event_generator())
