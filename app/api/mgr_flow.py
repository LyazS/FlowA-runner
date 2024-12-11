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
from datetime import datetime
from zoneinfo import ZoneInfo
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
    FARunResponse,
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
    FAWorkflowNodeResult,
    FAWorkflowResult,
    FAWorkflow,
    FAWorkflowLocation,
    FAWorkflowUpdateRequset,
    FAWorkflowReadRequest,
    FAWorkflowOperationResponse,
    FAWorkflowBaseInfo,
    FAResultBaseInfo,
)
from app.services.FARunner import FARunner
from app.db.session import get_db_ctxmgr
from app.models.fastore import (
    FAWorkflowModel,
    FAWorkflowResultModel,
    FAWorkflowNodeResultModel,
)
from sqlalchemy import select, update, exc, exists, delete

router = APIRouter()


# @router.get("/historys")
# async def get_history():
#     runnertid = await ALL_TASKS_MGR.getAllTaskID()
#     historys: List[FAWorkflow] = []
#     for tid in runnertid:
#         farunner: FARunner = await ALL_TASKS_MGR.get(tid)
#         if farunner:
#             historys.append(
#                 FAWorkflow(
#                     name=farunner.name,
#                     vflow=None,
#                     historys=FAWorkflowResult(
#                         tid=tid,
#                         noderesult=None,
#                         status=farunner.status,
#                         starttime=farunner.starttime,
#                         endtime=farunner.endtime,
#                     ),
#                     isCache=True,
#                 )
#             )
#     runnertid_set = set(runnertid)
#     for file in await aiofiles_os.listdir(settings.HISTORY_FOLDER):
#         if file.endswith(".json"):
#             tid = file.split(".")[0]
#             if tid not in runnertid_set:
#                 historys.append(
#                     FAWorkflow(
#                         name=tid,
#                         vflow=None,
#                         historys=None,
#                         isCache=False,
#                     )
#                 )
#     return historys


# @router.post("/loadhistory")
# async def load_history(tid: str):
#     test_farunner: FARunner = await ALL_TASKS_MGR.get(tid)
#     if test_farunner:
#         return FAWorkflow(
#             name=test_farunner.name,
#             vflow=test_farunner.oriflowdata,
#             historys=FAWorkflowResult(
#                 tid=tid,
#                 noderesult=None,
#                 status=test_farunner.status,
#                 starttime=test_farunner.starttime,
#                 endtime=test_farunner.endtime,
#             ),
#             isCache=True,
#         )
#     else:
#         check_path = f"{settings.HISTORY_FOLDER}/{tid}.json"
#         try:
#             if await aiofiles_os.path.exists(check_path):
#                 async with aiofiles.open(check_path, mode="r", encoding="utf-8") as f:
#                     data = json.loads(await f.read())
#                     his = FAWorkflow.model_validate(data)
#                     await ALL_TASKS_MGR.create(his.historys.tid)
#                     await (await ALL_TASKS_MGR.get(his.historys.tid)).loadHistory(his)
#                     return FAWorkflow(
#                         name=his.name,
#                         vflow=his.vflow,
#                         historys=FAWorkflowResult(
#                             tid=tid,
#                             noderesult=None,
#                             status=his.historys.status,
#                             starttime=his.historys.starttime,
#                             endtime=his.historys.endtime,
#                         ),
#                         isCache=True,
#                     )
#                 pass
#         except Exception as e:
#             errmsg = traceback.format_exc()
#             logger.error(f"load history error: {errmsg}")
#             pass
#         pass
#     pass
#     return None


# @router.get("/workflows")
# async def get_workflows():
#     workflows: List[str] = []
#     if await aiofiles_os.path.exists(settings.WORKFLOW_FOLDER):
#         for file in await aiofiles_os.listdir(settings.WORKFLOW_FOLDER):
#             if file.endswith(".json"):
#                 file_name = file.split(".")[0]
#                 workflows.append(
#                     FAWorkflow(
#                         name=file_name,
#                         vflow=None,
#                         historys=None,
#                         isCache=False,
#                     )
#                 )
#             pass
#         pass
#     return workflows


# @router.post("/saveworkflow")
# async def save_workflow(save_request: FAWorkflow):
#     name = save_request.name
#     # vflow = save_request.vflow
#     workflow_path = f"{settings.WORKFLOW_FOLDER}/{name}.json"
#     async with aiofiles.open(workflow_path, mode="w", encoding="utf-8") as f:
#         await f.write(save_request.model_dump_json(indent=4))
#     pass


# @router.post("/getworkflow")
# async def get_workflow(name: str):
#     workflow_path = f"{settings.WORKFLOW_FOLDER}/{name}.json"
#     if await aiofiles_os.path.exists(workflow_path):
#         try:
#             async with aiofiles.open(workflow_path, mode="r", encoding="utf-8") as f:
#                 data = FAWorkflow.model_validate(json.loads(await f.read()))
#                 return data
#         except Exception as e:
#             errmsg = traceback.format_exc()
#             logger.error(f"load workflow error: {errmsg}")
#             pass
#         pass
#     else:
#         return None


@router.post("/create")
async def create_workflow(create_request: FAWorkflow):
    try:
        async with get_db_ctxmgr() as db:
            db_wf = FAWorkflowModel(
                name=create_request.name,
                vflow=create_request.vflow,
                last_modified=datetime.now(ZoneInfo("Asia/Shanghai")),
            )
            db.add(db_wf)
            await db.commit()
            await db.refresh(db_wf)
            return FAWorkflowOperationResponse(success=True, data=db_wf.wid)
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"create workflow error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)


@router.get("/readall")
async def read_all_workflows():
    try:
        async with get_db_ctxmgr() as db:
            stmt = select(FAWorkflowModel.wid, FAWorkflowModel.name)
            db_result = await db.execute(stmt)
            db_workflows = db_result.mappings().all()
            result = []
            for db_wf in db_workflows:
                result.append(
                    FAWorkflowBaseInfo(
                        wid=db_wf["wid"],
                        name=db_wf["name"],
                    )
                )
            return FAWorkflowOperationResponse(success=True, data=result)
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"read all workflows error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)


@router.post("/read")
async def read_workflow(read_request: FAWorkflowReadRequest):
    try:
        async with get_db_ctxmgr() as db:
            stmt = select(exists().where(FAWorkflowModel.wid == read_request.wid))
            db_result = await db.execute(stmt)
            db_exists = db_result.scalar()
            if db_exists:
                result = []
                for location in read_request.locations:
                    if location == FAWorkflowLocation.name:
                        stmt = select(FAWorkflowModel.name).filter(
                            FAWorkflowModel.wid == read_request.wid
                        )
                        db_result = await db.execute(stmt)
                        name = db_result.scalars().first()
                        result.append(name)
                    elif location == FAWorkflowLocation.vflow:
                        stmt = select(FAWorkflowModel.vflow).filter(
                            FAWorkflowModel.wid == read_request.wid
                        )
                        db_result = await db.execute(stmt)
                        vflow = db_result.scalars().first()
                        result.append(vflow)
                    elif location == FAWorkflowLocation.results:
                        stmt = (
                            select(FAWorkflowResultModel)
                            .filter(FAWorkflowResultModel.tid == read_request.tid)
                            .filter(FAWorkflowResultModel.wid == read_request.wid)
                        )
                        db_result = await db.execute(stmt)
                        db_result = db_result.scalars().first()
                        wfresult = FAWorkflowResult(
                            tid=db_result.tid,
                            usedvflow=db_result.usedvflow,
                            noderesult=db_result.noderesults,
                            status=db_result.status,
                            starttime=db_result.starttime,
                            endtime=db_result.endtime,
                        )
                        result.append(wfresult)
                return FAWorkflowOperationResponse(success=True, data=result)
            else:
                return FAWorkflowOperationResponse(
                    success=False, message="Workflow not found"
                )
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"read workflow error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)


@router.post("/update")
async def update_workflow(update_request: FAWorkflowUpdateRequset):
    try:
        async with get_db_ctxmgr() as db:
            stmt = select(exists().where(FAWorkflowModel.wid == update_request.wid))
            db_result = await db.execute(stmt)
            db_exists = db_result.scalar()
            if db_exists:
                if update_request.location == FAWorkflowLocation.name and isinstance(
                    update_request.data, str
                ):
                    await db.execute(
                        update(FAWorkflowModel)
                        .where(FAWorkflowModel.wid == update_request.wid)
                        .values(name=update_request.data)
                    )
                    await db.commit()
                elif update_request.location == FAWorkflowLocation.vflow and isinstance(
                    update_request.data, dict
                ):
                    await db.execute(
                        update(FAWorkflowModel)
                        .where(FAWorkflowModel.wid == update_request.wid)
                        .values(vflow=update_request.data)
                    )
                    await db.commit()
                else:
                    pass
                pass
                return FAWorkflowOperationResponse(success=True)
            else:
                return FAWorkflowOperationResponse(
                    success=False, message="Workflow not found"
                )
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"update workflow error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)


@router.post("/delete")
async def delete_workflow(wid: int):
    try:
        async with get_db_ctxmgr() as db:
            stmt = select(exists().where(FAWorkflowModel.wid == wid))
            db_result = await db.execute(stmt)
            db_exists = db_result.scalar()
            if db_exists:
                await db.execute(
                    delete(FAWorkflowModel).where(FAWorkflowModel.wid == wid)
                )
                await db.commit()
                return FAWorkflowOperationResponse(success=True)
            else:
                return FAWorkflowOperationResponse(
                    success=False, message="Workflow not found"
                )
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"delete workflow error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)


@router.get("/readallresults")
async def read_all_results(wid: int):
    try:
        async with get_db_ctxmgr() as db:
            stmt = select(
                FAWorkflowResultModel.tid,
                FAWorkflowResultModel.status,
                FAWorkflowResultModel.starttime,
                FAWorkflowResultModel.endtime,
            ).filter(FAWorkflowResultModel.wid == wid)
            db_result = await db.execute(stmt)
            db_results = db_result.mappings().all()
            result = []
            for db_res in db_results:
                result.append(
                    FAResultBaseInfo(
                        tid=db_res["tid"],
                        status=db_res["status"],
                        starttime=db_res["starttime"],
                        endtime=db_res["endtime"],
                    )
                )
            return FAWorkflowOperationResponse(success=True, data=result)
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"read all results error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)


@router.post("/loadresult")
async def load_result(wid: int, tid: str):
    try:
        async with get_db_ctxmgr() as db:
            pass
    except Exception as e:
        errmsg = traceback.format_exc()
        logger.error(f"load result error: {errmsg}")
        return FAWorkflowOperationResponse(success=False, message=errmsg)
