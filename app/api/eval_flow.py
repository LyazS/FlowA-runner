from typing import List, Dict
import asyncio
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.vfnode import VFlowData
from app.services.FAWorker import FAEvaluator

router = APIRouter()


@router.get("/eval")
async def eval_flow(flowdata: VFlowData):
    if settings.DEBUG:
        await asyncio.sleep(1)
    ffe = FAEvaluator()
    result = await ffe.eval(flowdata)
    return result
