from typing import List, Dict
import asyncio
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.vfnode import VFlowData
from app.services.FAValidator import FAValidator

router = APIRouter()


@router.post("/validate")
async def validate_flow(fa_req):
    if settings.DEBUG:
        await asyncio.sleep(1)
    ffe = FAValidator()
    flowdata = fa_req.vflow
    result = await ffe.validate(flowdata)
    return result
