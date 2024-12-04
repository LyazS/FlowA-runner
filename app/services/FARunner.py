import asyncio
from typing import Dict, List, TYPE_CHECKING
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from app.schemas.fanode import FARunnerStatus
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
)

if TYPE_CHECKING:
    from app.nodes import FABaseNode


class FARunner:
    def __init__(self, tid: str, flowdata: VFlowData):
        self.tid = tid
        self.flowdata = flowdata
        self.nodes: Dict[str, "FABaseNode"] = {}
        self.status: FARunnerStatus = FARunnerStatus.Pending
        pass

    def addNode(self, nid, node: "FABaseNode"):
        self.nodes[nid] = node
        pass

    def getNode(self, nid: str) -> "FABaseNode":
        return self.nodes[nid]

    def buildNodes(self):
        from app.nodes.basenode import FANodeWaitStatus
        from app.nodes import FANODECOLLECTION

        # 初始化大图节点，即parentNode == None
        for nodeinfo in self.flowdata.nodes:
            if nodeinfo.parentNode == None:
                self.addNode(
                    nodeinfo.id,
                    (FANODECOLLECTION[nodeinfo.data.ntype])(
                        self.tid,
                        nodeinfo,
                    ),
                )
            pass
        # 构建节点连接关系
        for edgeinfo in self.flowdata.edges:
            if edgeinfo.source in self.nodes and edgeinfo.target in self.nodes:
                if (
                    self.getNode(edgeinfo.source).parentNode != None
                    or self.getNode(edgeinfo.target).parentNode != None
                ):
                    continue
                source_handle = edgeinfo.sourceHandle
                target_handle = edgeinfo.targetHandle
                self.getNode(edgeinfo.target).waitEvents.append(
                    self.getNode(edgeinfo.source).doneEvent
                )
                self.getNode(edgeinfo.target).waitStatus.append(
                    FANodeWaitStatus(
                        nid=edgeinfo.source,
                        output=source_handle,
                    )
                )
        pass

    async def run(self):
        self.buildNodes()
        # 启动所有节点
        self.status = FARunnerStatus.Running
        tasks = []
        # 当前只有根节点，所以直接启动即可
        for nid in self.nodes:
            tasks.append(self.nodes[nid].invoke())
        # 等待所有节点完成
        await asyncio.gather(*tasks)
        self.status = FARunnerStatus.Success
        ALL_MESSAGES_MGR.put(
            self.tid,
            SSEResponse(
                event=SSEResponseType.flowfinish,
                data=None,
            ),
        )
        pass
