from typing import Dict, List
from app.schemas.validation import VarItem, ValidationResult
from app.schemas.node import NodeConnectionDataType
from app.schemas.vfnode import VFlowData
from app.nodes import FABaseNode, FANODECOLLECTION


class FAEvaluator:
    def __init__(self):
        self.nodes: Dict[str, FABaseNode] = {}
        self.connectGraph = {}
        pass

    def get_handle_connections(self, nid, type, hid):
        if nid in self.connectGraph:
            if type == "source" and hid in self.connectGraph[nid]["source"]:
                return self.connectGraph[nid]["source"][hid]
            elif type == "target" and hid in self.connectGraph[nid]["target"]:
                return self.connectGraph[nid]["target"][hid]
        return None

    def recursive_find_variables(
        self,
        nid: str,
        find_self: bool = False,
        find_attach: bool = False,
        find_all_input: bool = False,
        find_input: List[str] = None,
        find_all_output: bool = False,
        find_output: List[str] = None,
    ) -> List[VarItem]:
        if find_input is None:
            find_input = []
        if find_output is None:
            find_output = []

        result = []
        the_node = self.nodes[nid]

        if find_all_input:
            find_input = list(the_node.data.connections.inputs.keys())
        if find_all_output:
            find_output = list(the_node.data.connections.outputs.keys())

        if find_self:
            result.extend(self.find_var_from_io(nid, "self", "self"))
        if find_attach:
            result.extend(self.find_var_from_io(nid, "attach", "attach"))

        for hid in find_input:
            result.extend(self.find_var_from_io(nid, hid, "input"))
        for hid in find_output:
            result.extend(self.find_var_from_io(nid, hid, "output"))

        return result

    def find_var_from_io(
        self,
        nid: str,
        hid: str,
        findtype: str,
    ) -> List[VarItem]:
        result = []
        the_node = self.nodes[nid]  # 假设这个函数在其他地方定义

        # 根据类型获取connection数据
        if findtype == "self":
            connection = the_node.data.connections.self[hid].data
        elif findtype == "attach":
            connection = the_node.data.connections.attach[hid].data
        elif findtype == "input":
            connection = the_node.data.connections.inputs[hid].data
        elif findtype == "output":
            connection = the_node.data.connections.outputs[hid].data

        for c_data in connection.values():
            if c_data.type == NodeConnectionDataType.FromInner:
                result.append(
                    VarItem(
                        nodeId=nid,
                        nlabel=the_node.data.label,
                        dpath=c_data.path,
                        dlabel=the_node.data.getContent(c_data.path[0])
                        .byId[c_data.path[1]]
                        .label,
                        dkey=the_node.data.getContent(c_data.path[0])
                        .byId[c_data.path[1]]
                        .key,
                        dtype=the_node.data.getContent(c_data.path[0])
                        .byId[c_data.path[1]]
                        .type,
                    )
                )

            elif c_data.type == NodeConnectionDataType.FromOuter:
                # 对于上一个节点，递归搜索上个节点的对应输出handle
                in_hid = c_data.inputKey
                edges = self.get_handle_connections(nid, "target", in_hid)
                for edge in edges:
                    src_nid = edge["nid"]
                    src_hid = edge["hid"]
                    result.extend(
                        self.recursive_find_variables(
                            src_nid, False, False, False, [], False, [src_hid]
                        )
                    )

            elif c_data.type == NodeConnectionDataType.FromAttached:
                # 对于子节点的处理
                result.extend(
                    self.recursive_find_variables(
                        the_node.data.nesting.attached_nodes[c_data.atype].nid,
                        c_data.atype == "output",
                        False,
                        False,
                        [],
                        c_data.atype == "input",
                        [],
                    )
                )

            elif c_data.type == NodeConnectionDataType.FromParent:
                # 如果是父节点，递归搜索父节点的所有输入handle
                result.extend(
                    self.recursive_find_variables(
                        the_node.parentNode, False, True, True, [], False, []
                    )
                )

        return result

    async def eval(self, flowdata: VFlowData) -> Dict[str, ValidationResult]:
        # 初始化所有节点
        for nodeinfo in flowdata.nodes:
            node = FANODECOLLECTION[nodeinfo.data.ntype](nodeinfo)
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
        # 逐个节点验证，主要验证变量是否合法
        validNodes = {}
        for nid in self.nodes.keys():
            node = self.nodes[nid]
            selfVarItems = self.recursive_find_variables(
                nid, True, False, False, [], False, []
            )
            selfVars = [
                f"{item.nodeId}/{item.dpath[0]}/{item.dpath[1]}"
                for item in selfVarItems
            ]
            print(f"node {node.data.label} selfVars: {selfVars}")
            validNodes[node.id] = node.validate(selfVars)
        pass
        return validNodes
