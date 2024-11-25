from typing import List, Union, Dict
import asyncio
from pydantic import BaseModel
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeData
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError


class FANodeWaitStatus(BaseModel):
    nid: str
    output: str
    pass


class FABaseNode:
    def __init__(self, nodeinfo: VFNodeInfo):
        self.id = nodeinfo.id
        self.data: VFNodeData = nodeinfo.data
        self.ntype: str = nodeinfo.data.ntype
        self.parentNode = nodeinfo.parentNode

        self.doneEvent = asyncio.Event()
        self.waitEvents: List[asyncio.Event] = []
        self.waitType = FANodeWaitType.AND

        self.waitStatus: List[FANodeWaitStatus] = []
        self.status: Dict[str, FANodeStatus] = {
            oname: FANodeStatus.Pending
            for oname in self.data.connections.outputs.keys()
        }
        pass

    async def _run(self, getNodes: Dict[str, "FABaseNode"]):
        await asyncio.gather(*(event.wait() for event in self.waitEvents))
        waitFunc = all if self.waitType == FANodeWaitType.AND else any
        hasError = waitFunc(
            [
                getNodes[status.nid].status[status.output] == FANodeStatus.Error
                for status in self.waitStatus
            ]
        )
        hasCanceled = waitFunc(
            [
                getNodes[status.nid].status[status.output] == FANodeStatus.Canceled
                for status in self.waitStatus
            ]
        )

        # 前置节点出错或取消，本节点取消运行
        if hasError or hasCanceled:
            self.status = FANodeStatus.Canceled
            self.doneEvent.set()
            return

        try:
            # 前置节点全部成功，本节点运行
            self.status = FANodeStatus.Running
            await self.run(getNodes)
            self.status = FANodeStatus.Success
            pass
        except Exception as e:
            self.status = FANodeStatus.Error
            raise e
        finally:
            self.doneEvent.set()
        pass

    async def run(self, getNodes: Dict[str, "FABaseNode"]):
        pass

    def init(self, *args, **kwargs):
        pass

    def validate(self, selfVars: List[str]) -> Union[ValidationError, None]:
        return None
