from typing import List, Dict
import asyncio
import uuid
from fastapi import APIRouter
from fastapi.background import BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from app.core.config import settings
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
)

router = APIRouter()


@router.post("/run")
async def run_flow(
    fa_req: FARunRequest,
    background_tasks: BackgroundTasks,
) -> FARunResponse:
    if settings.DEBUG:
        await asyncio.sleep(1)
    taskid = str(uuid.uuid4()).replace("-", "")
    fav = FAValidator()
    flowdata = fa_req.vflow
    validate_result = await fav.validate(taskid, flowdata)
    if len(validate_result) > 0:
        return FARunResponse(
            success=False,
            tid=None,
            validation_errors=validate_result,
        )
    # 通过检查 =============================================
    await ALL_TASKS_MGR.create(taskid, flowdata)
    background_tasks.add_task(ALL_TASKS_MGR.run, taskid)
    return FARunResponse(success=True, tid=taskid)


@router.get("/progress")
async def get_task_progress(taskid: str):
    async def event_generator():
        try:
            # 第一步，创建消息管理器
            # 推送整体情况
            # 推送剩余情况
            # 在进度完成后，叫前端post获取一次完整结果
            await ALL_MESSAGES_MGR.create(taskid)
            farunner: FARunner = ALL_TASKS_MGR.get(taskid)
            all_nodes_data: List[SSEResponseData] = []
            for nid in farunner.nodes.keys():
                ndata = farunner.nodes[nid].getCurData()
                if ndata is None:
                    continue
                all_nodes_data.extend(ndata)
            ALL_MESSAGES_MGR.put(
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=all_nodes_data,
                ).model_dump_json()
            )
            pass
            while True:
                # 第二步,去检查各个未完成任务的进度
                p_msg = await ALL_MESSAGES_MGR.get(taskid)
                if p_msg is None:
                    continue
                yield p_msg
                ALL_MESSAGES_MGR.task_done(taskid)
                pass

        except Exception as e:
            pass
        finally:
            await ALL_MESSAGES_MGR.remove(taskid)
            pass

    return EventSourceResponse(event_generator())
