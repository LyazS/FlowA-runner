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
from app.schemas.vfnode import VFlowData
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
    FAWorkflowNodeResult,
    FAWorkflowResult,
    FAWorkflow,
    FAWorkflowLocation,
    FAWorkflowUpdateRequset,
    FAWorkflowReadRequest,
    FAWorkflowOperationResponse,
    FAWorkflowInfo,
    FAWorkflowNodeRequest,
)
from app.models.fastore import (
    FAWorkflowModel,
    FAReleasedWorkflowModel,
    FANodeCacheModel,
)
from app.nodes import FANODECOLLECTION
from app.nodes.basenode import FABaseNode

router = APIRouter()


@router.get("/nodeconfig")
async def nodeconfig(ntype: str):
    if ntype in FANODECOLLECTION:
        node: "FABaseNode" = FANODECOLLECTION[ntype]
        return FAWorkflowOperationResponse(success=True, data=node.getNodeConfig())
    else:
        return FAWorkflowOperationResponse(
            success=False,
            message=f"Node type {ntype} not found in FANODECOLLECTION",
        )
