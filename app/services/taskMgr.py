import asyncio
from typing import Callable, Awaitable, Any, Dict
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from .FARunner import FARunner


class TaskMgr:
    def __init__(self):
        self.task_runner: Dict[str, FARunner] = dict()
        self.lock = asyncio.Lock()

    async def create(self, tid: str):
        async with self.lock:
            if tid not in self.task_runner:
                self.task_runner[tid] = FARunner(tid)

    async def get(self, tid: str) -> FARunner:
        if tid in self.task_runner:
            return self.task_runner[tid]
        else:
            return None

    async def getAllTaskID(self):
        async with self.lock:
            return list(self.task_runner.keys())
        pass

    async def run(self, tid: str, oriflowdata):
        if tid in self.task_runner:
            await self.task_runner[tid].run(oriflowdata)

    async def stop(self, tid: str):
        pass

    async def remove(self, tid: str):
        async with self.lock:
            if tid in self.task_runner:
                del self.task_runner[tid]


ALL_TASKS_MGR = TaskMgr()
