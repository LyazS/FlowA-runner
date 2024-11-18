from typing import List, Dict
import asyncio
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/run")
async def run_flow():
    if settings.DEBUG:
        await asyncio.sleep(1)
    return None
