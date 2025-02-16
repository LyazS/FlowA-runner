import asyncio
from typing import Callable, Awaitable, Any, Dict
from .FARunner import FARunner
from app.schemas.fanode import FARunnerStatus


class TaskMgr:
    def __init__(self):
        self.task_runner: Dict[str, FARunner] = dict()
        self.lock = asyncio.Lock()

    async def create(self, wid: str):
        async with self.lock:
            if wid not in self.task_runner:
                self.task_runner[wid] = FARunner(wid)

    async def add(self, runner: FARunner):
        async with self.lock:
            self.task_runner[runner.wid] = runner

    async def get(self, wid: str) -> FARunner:
        if wid in self.task_runner:
            return self.task_runner[wid]
        else:
            return None

    async def getAllTaskID(self):
        async with self.lock:
            return list(self.task_runner.keys())
        pass

    async def run(self, wid: str, oriflowdata):
        if wid in self.task_runner:
            await self.task_runner[wid].run(oriflowdata)

    async def stop(self, wid: str):
        pass

    async def isRunning(self, wid: str) -> bool:
        if wid in self.task_runner:
            return self.task_runner[wid].status == FARunnerStatus.Running
        else:
            return False

    async def remove(self, wid: str):
        async with self.lock:
            if wid in self.task_runner:
                del self.task_runner[wid]


ALL_TASKS_MGR = TaskMgr()
