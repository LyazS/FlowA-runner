from typing import List, Dict, Optional
import asyncio
from pydantic import BaseModel
import traceback
from loguru import logger
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentDataType, VFNodeData, VFlowData
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
)
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR
from .basenode import FABaseNode


class FANode_iter_run(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        pass

    async def run(self) -> List[FANodeUpdateData]:
        from app.nodes.basenode import FANodeWaitStatus
        from app.nodes import FANODECOLLECTION

        flowdata: VFlowData = (await ALL_TASKS_MGR.get(self.tid)).flowdata
        child_infos: Dict[str, VFNodeInfo] = {}

        for nodeinfo in flowdata.nodes:
            if nodeinfo.parentNode == self.id:
                child_infos[nodeinfo.id] = nodeinfo
            pass
        pass
        for child_id, child_info in child_infos.items():
            if child_info.data.flags.isAttached:
                continue
            pass
        # # 构建节点连接关系
        # for edgeinfo in self.flowdata.edges:
        #     if edgeinfo.source in self.nodes and edgeinfo.target in self.nodes:
        #         if (
        #             self.getNode(edgeinfo.source).parentNode != None
        #             or self.getNode(edgeinfo.target).parentNode != None
        #         ):
        #             continue
        #         source_handle = edgeinfo.sourceHandle
        #         target_handle = edgeinfo.targetHandle
        #         self.getNode(edgeinfo.target).waitEvents.append(
        #             self.getNode(edgeinfo.source).doneEvent
        #         )
        #         self.getNode(edgeinfo.target).waitStatus.append(
        #             FANodeWaitStatus(
        #                 nid=edgeinfo.source,
        #                 output=source_handle,
        #             )
        #         )
        pass
