import asyncio
from typing import Dict, Optional


class ProjectMessageMgr:
    def __init__(self):
        self.message_queue: Dict[str, asyncio.Queue] = dict()
        self.lock = asyncio.Lock()

    async def create(self, task_name: str):
        async with self.lock:
            if task_name not in self.message_queue:
                self.message_queue[task_name] = asyncio.Queue()

    def put(self, task_name: str, message: str):
        if task_name in self.message_queue:
            self.message_queue[task_name].put_nowait(message)

    async def get(self, task_name: str) -> Optional[str]:
        if task_name in self.message_queue:
            return await self.message_queue[task_name].get()
        return None

    def task_done(self, task_name: str):
        if task_name in self.message_queue:
            self.message_queue[task_name].task_done()

    async def remove(self, task_name: str):
        async with self.lock:
            if task_name in self.message_queue:
                del self.message_queue[task_name]


ALL_MESSAGES_MGR = ProjectMessageMgr()
