import asyncio
from typing import Callable, Awaitable, Any, Dict
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from .FARunner import FARunner


class TaskMgr:
    def __init__(self):
        self.task_runner: Dict[str, FARunner] = dict()
        self.lock = asyncio.Lock()

    async def create(self, tid: str, flowdata: VFlowData):
        async with self.lock:
            if tid not in self.task_runner:
                self.task_runner[tid] = FARunner(tid, flowdata)

    async def get(self, tid: str) -> FARunner:
        if tid in self.task_runner:
            return self.task_runner[tid]
        else:
            return None

    async def run(self, tid: str):
        if tid in self.task_runner:
            await self.task_runner[tid].run()

    async def stop(self, tid: str):
        pass

    async def remove(self, tid: str):
        async with self.lock:
            if tid in self.task_runner:
                del self.task_runner[tid]


ALL_TASKS_MGR = TaskMgr()
