import asyncio
from typing import Dict, List
from app.schemas.farequest import VarItem, ValidationError
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from app.schemas.fanode import FARunnerStatus
from app.nodes import FABaseNode, FANODECOLLECTION
from app.nodes.basenode import FANodeWaitStatus


class FARunner:
    def __init__(self, tid: str, flowdata: VFlowData):
        self.tid = tid
        self.nodes: Dict[str, FABaseNode] = {}
        self.status: FARunnerStatus = FARunnerStatus.Pending
        pass
        # 初始化所有节点
        for nodeinfo in flowdata.nodes:
            self.nodes[nodeinfo.id] = (FANODECOLLECTION[nodeinfo.data.ntype])(
                self.tid,
                nodeinfo,
            )
            pass
        # 构建节点连接关系
        for edgeinfo in flowdata.edges:
            if edgeinfo.source in self.nodes and edgeinfo.target in self.nodes:
                source_handle = edgeinfo.sourceHandle
                target_handle = edgeinfo.targetHandle
                self.nodes[edgeinfo.target].waitEvents.append(
                    self.nodes[edgeinfo.source].doneEvent
                )
                self.nodes[edgeinfo.target].waitStatus.append(
                    FANodeWaitStatus(
                        nid=edgeinfo.source,
                        output=source_handle,
                    )
                )
        pass

    async def run(self):
        # 启动所有节点
        self.status = FARunnerStatus.Running
        tasks = []
        for nid in self.nodes:
            tasks.append(self.nodes[nid].run(self.nodes))
        # 等待所有节点完成
        await asyncio.gather(*tasks)
        self.status = FARunnerStatus.Success
        pass
