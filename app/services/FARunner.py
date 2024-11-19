from typing import Dict, List
from app.schemas.farequest import VarItem, ValidationResult
from app.schemas.vfnode import VFNodeConnectionDataType, VFlowData
from app.nodes import FABaseNode, FANODECOLLECTION


class FARunner:
    def __init__(self):
        self.nodes: Dict[str, FABaseNode] = {}
        self.connectGraph = {}
        pass

    async def run(self, flowdata: VFlowData) -> Dict[str, ValidationResult]:
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
                if edgeinfo.source not in self.connectGraph:
                    self.connectGraph[edgeinfo.source] = {"source": {}, "target": {}}
                    pass
                if source_handle not in self.connectGraph[edgeinfo.source]:
                    self.connectGraph[edgeinfo.source]["source"][source_handle] = []
                    pass
                self.connectGraph[edgeinfo.source]["source"][source_handle].append(
                    {"nid": edgeinfo.target, "hid": target_handle}
                )
                pass
                if edgeinfo.target not in self.connectGraph:
                    self.connectGraph[edgeinfo.target] = {"source": {}, "target": {}}
                    pass
                if target_handle not in self.connectGraph[edgeinfo.target]:
                    self.connectGraph[edgeinfo.target]["target"][target_handle] = []
                    pass
                self.connectGraph[edgeinfo.target]["target"][target_handle].append(
                    {"nid": edgeinfo.source, "hid": source_handle}
                )
                pass
        return None
