from typing import List, Dict, Optional
from typing import Annotated
from fastapi import Body, FastAPI
import asyncio
import uuid
import traceback
import json
import aiofiles
from aiofiles import os as aiofiles_os
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
    FARunnerHistory,
    FARunnerHistorys,
    RunnerStoreHistory,
    FARunnerWorkflows,
    SaveWorkflowRequest,
)
from app.services.FARunner import FARunner

router = APIRouter()


@router.get("/historys")
async def get_history():
    runnertid = await ALL_TASKS_MGR.getAllTaskID()
    historys: List[FARunnerHistory] = []
    for tid in runnertid:
        farunner: FARunner = await ALL_TASKS_MGR.get(tid)
        if farunner:
            historys.append(
                FARunnerHistory(
                    tid=tid,
                    status=farunner.status,
                    starttime=farunner.starttime,
                    endtime=farunner.endtime,
                )
            )
    runnertid_set = set(runnertid)
    for file in await aiofiles_os.listdir(settings.HISTORY_FOLDER):
        if file.endswith(".json"):
            tid = file.split(".")[0]
            if tid not in runnertid_set:
                async with aiofiles.open(
                    f"{settings.HISTORY_FOLDER}/{tid}.json", mode="r", encoding="utf-8"
                ) as f:
                    data = json.loads(await f.read())
                    his = RunnerStoreHistory.model_validate(data)
                    await ALL_TASKS_MGR.create(his.tid)
                    (await ALL_TASKS_MGR.get(his.tid)).loadHistory(his)
                    historys.append(
                        FARunnerHistory(
                            tid=his.tid,
                            status=his.status,
                            starttime=his.starttime,
                            endtime=his.endtime,
                        )
                    )
    return FARunnerHistorys(historys=historys)


@router.post("/loadhistory")
async def load_history(tid: str) -> Optional[dict]:
    test_farunner: FARunner = await ALL_TASKS_MGR.get(tid)
    if test_farunner:
        return test_farunner.oriflowdata
    else:
        check_path = f"{settings.HISTORY_FOLDER}/{tid}.json"
        if await aiofiles_os.path.exists(check_path):
            async with aiofiles.open(check_path, mode="r", encoding="utf-8") as f:
                data = json.loads(await f.read())
                his = RunnerStoreHistory.model_validate(data)
                await ALL_TASKS_MGR.create(his.tid)
                (await ALL_TASKS_MGR.get(his.tid)).loadHistory(his)
                return his.oriflowdata
            pass
        pass
    pass
    return None


@router.get("/workflows")
async def get_workflows():
    workflows: List[str] = []
    if await aiofiles_os.path.exists(settings.WORKFLOW_FOLDER):
        for file in await aiofiles_os.listdir(settings.WORKFLOW_FOLDER):
            if file.endswith(".json"):
                file_name = file.split(".")[0]
                workflows.append(file_name)
            pass
        pass
    return FARunnerWorkflows(workflows=workflows)


@router.post("/saveworkflow")
async def save_workflow(save_request: SaveWorkflowRequest):
    name = save_request.name
    # vflow = save_request.vflow
    workflow_path = f"{settings.WORKFLOW_FOLDER}/{name}.json"
    async with aiofiles.open(workflow_path, mode="w", encoding="utf-8") as f:
        await f.write(json.dumps(save_request.model_dump_json()))
    pass


@router.post("/getworkflow")
async def get_workflow(name: Annotated[str, Body()]):
    workflow_path = f"{settings.WORKFLOW_FOLDER}/{name}.json"
    if await aiofiles_os.path.exists(workflow_path):
        async with aiofiles.open(workflow_path, mode="r", encoding="utf-8") as f:
            data = json.loads(await f.read())
            return data
    else:
        return None
