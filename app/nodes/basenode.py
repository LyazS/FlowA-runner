from typing import List, Dict, Optional
import asyncio
from pydantic import BaseModel
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeData
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
)
from app.services.messageMgr import ALL_MESSAGES_MGR


class FANodeWaitStatus(BaseModel):
    nid: str
    output: str
    pass


class NodeCancelException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FABaseNode:
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        self.tid = tid
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
        try:
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
                raise NodeCancelException("前置节点出错或取消，本节点取消运行")

            # 前置节点全部成功，本节点开始运行
            self.status = FANodeStatus.Running
            ALL_MESSAGES_MGR.put(
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=SSEResponseData(
                        nid=self.id,
                        updates=[
                            FANodeUpdateData(
                                type=FANodeUpdateType.overwrite,
                                path=["state", "status"],
                                data=FANodeStatus.Running,
                            )
                        ],
                    ),
                ).model_dump_json()
            )
            updateDatas = await self.run(getNodes)
            # 运行成功
            nodeUpdateDatas = []
            if updateDatas:
                nodeUpdateDatas.extend(updateDatas)
                pass
            self.status = FANodeStatus.Success
            nodeUpdateDatas.append(
                FANodeUpdateData(
                    type=FANodeUpdateType.overwrite,
                    path=["state", "status"],
                    data=FANodeStatus.Success,
                )
            )
            ALL_MESSAGES_MGR.put(
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=SSEResponseData(
                        nid=self.id,
                        updates=nodeUpdateDatas,
                    ),
                ).model_dump_json()
            )
            pass
        except NodeCancelException as e:
            self.status = FANodeStatus.Canceled
            ALL_MESSAGES_MGR.put(
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=SSEResponseData(
                        nid=self.id,
                        updates=[
                            FANodeUpdateData(
                                type=FANodeUpdateType.overwrite,
                                path=["state", "status"],
                                data=FANodeStatus.Canceled,
                            )
                        ],
                    ),
                ).model_dump_json()
            )
            pass
        except Exception as e:
            self.status = FANodeStatus.Error
            ALL_MESSAGES_MGR.put(
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=SSEResponseData(
                        nid=self.id,
                        updates=[
                            FANodeUpdateData(
                                type=FANodeUpdateType.overwrite,
                                path=["state", "status"],
                                data=FANodeStatus.Error,
                            )
                        ],
                    ),
                ).model_dump_json()
            )
        finally:
            self.doneEvent.set()
        pass

    async def run(self, getNodes: Dict[str, "FABaseNode"]) -> List[FANodeUpdateData]:
        pass

    def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return None

    def init(self, *args, **kwargs):
        pass

    def validate(self, selfVars: List[str]) -> Optional[ValidationError]:
        return None
