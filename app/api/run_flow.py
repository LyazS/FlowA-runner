from typing import List, Dict
import asyncio
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.vfnode import VFlowData
from app.schemas.farequest import FARunRequest
from app.services.FARunner import FARunner
from app.services.FAValidator import FAValidator

router = APIRouter()


@router.post("/run")
async def run_flow(fa_req: FARunRequest):
    if settings.DEBUG:
        await asyncio.sleep(1)
    fav = FAValidator()
    flowdata = fa_req.vflow
    result = await fav.validate(flowdata)
    far = FARunner()
    return result
