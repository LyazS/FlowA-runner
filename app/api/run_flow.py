from typing import List, Dict
import asyncio
import uuid
from fastapi import APIRouter
from fastapi.background import BackgroundTasks
from app.core.config import settings
from app.schemas.vfnode import VFlowData
from app.schemas.farequest import FARunRequest, FARunResponse
from app.services.FARunner import FARunner
from app.services.FAValidator import FAValidator

router = APIRouter()


@router.post("/run")
async def run_flow(
    fa_req: FARunRequest,
    background_tasks: BackgroundTasks,
) -> FARunResponse:
    if settings.DEBUG:
        await asyncio.sleep(1)
    fav = FAValidator()
    flowdata = fa_req.vflow
    validate_result = await fav.validate(flowdata)
    if len(validate_result) > 0:
        return FARunResponse(
            success=False,
            tid=None,
            validation_errors=validate_result,
        )
    # 通过检查 =============================================
    taskid = str(uuid.uuid4()).replace("-", "")
    far = FARunner(taskid)
    background_tasks.add_task(far.run, flowdata)
    return FARunResponse(
        success=True,
        tid=taskid,
    )
