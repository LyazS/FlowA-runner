import asyncio
from typing import Dict, List
from app.schemas.farequest import VarItem, ValidationError
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from app.nodes import FABaseNode, FANODECOLLECTION
from app.nodes.basenode import FANodeWaitStatus


class FARunner:
    def __init__(self, tid: str):
        self.nodes: Dict[str, FABaseNode] = {}
        self.tid = tid
        pass

    async def run(self, flowdata: VFlowData) -> Dict[str, ValidationError]:
        # 初始化所有节点
        for nodeinfo in flowdata.nodes:
            node = (FANODECOLLECTION[nodeinfo.data.ntype])(nodeinfo)
            self.nodes[nodeinfo.id] = node
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
        # 启动所有节点
        tasks = []
        for nid in self.nodes:
            tasks.append(self.nodes[nid].run(self.nodes))
        await asyncio.gather(*tasks)
        return None
