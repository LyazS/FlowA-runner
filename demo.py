import asyncio
import uuid
from typing import List, Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel
import json


class NodePayloadsData(BaseModel):
    label: str
    type: str
    key: str
    data: Any
    hid: Optional[str] = None
    oid: Optional[str] = None
    pass


class NodePayloads(BaseModel):
    byId: Dict[str, NodePayloadsData]
    order: List[str]
    pass


class NodeConnectionDataType(Enum):
    FromOuter = "FromOuter"
    FromAttached = "FromAttached"
    FromParent = "FromParent"
    FromInner = "FromInner"
    pass


class NodeConnectionData(BaseModel):
    type: NodeConnectionDataType
    inputKey: Optional[str] = None
    atype: Optional[str] = None
    path: Optional[List[str]] = None
    useid: Optional[List[str]] = None
    pass


class NodeConnectionType(Enum):
    self = "self"
    attach = "attach"
    inputs = "inputs"
    outputs = "outputs"
    callbackUsers = "callbackUsers"
    callbackFuncs = "callbackFuncs"
    pass


class NodeConnection(BaseModel):
    label: str
    data: Dict[str, NodeConnectionData]
    pass


class NodeConnections(BaseModel):
    self: Optional[Dict[str, NodeConnection]] = None
    attach: Optional[Dict[str, NodeConnection]] = None
    inputs: Optional[Dict[str, NodeConnection]] = None
    outputs: Optional[Dict[str, NodeConnection]] = None
    callbackUsers: Optional[Dict[str, NodeConnection]] = None
    callbackFuncs: Optional[Dict[str, NodeConnection]] = None
    pass


class NodeFlags(BaseModel):
    isNested: bool
    isAttached: bool
    isDisabled: bool


class NodeAttaching(BaseModel):
    type: str
    pos: str


class NodeAttachedNode(BaseModel):
    ntype: str
    nid: str
    apos: str


class NodePadding(BaseModel):
    top: int
    bottom: int
    left: int
    right: int


class NodeSize(BaseModel):
    width: float
    height: float


class NodeNesting(BaseModel):
    pad: NodePadding
    attached_pad: NodePadding
    attached_nodes: Dict[str, NodeAttachedNode]


class NodeData(BaseModel):
    ntype: str
    vtype: str
    flags: NodeFlags
    label: str
    placeholderlabel: str
    parentNode: Optional[str] = None
    size: Optional[NodeSize] = None
    min_size: Optional[NodeSize] = None
    attaching: Optional[NodeAttaching] = None
    nesting: Optional[NodeNesting] = None
    connections: Optional[NodeConnections] = None
    payloads: Optional[NodePayloads] = None
    results: Optional[NodePayloads] = None
    pass

    def get(self, path: List[str]):
        pass

    def getContent(self, content_name: str) -> NodePayloads:
        if content_name == "payloads":
            return self.payloads
        elif content_name == "results":
            return self.results


class VFNodePosition(BaseModel):
    x: float
    y: float
    pass


class VFNodeInfo(BaseModel):
    id: str
    type: str
    position: VFNodePosition
    data: NodeData
    parentNode: Optional[str] = None
    pass


class VFEdgeInfo(BaseModel):
    id: str
    type: str
    source: str
    target: str
    sourceHandle: str
    targetHandle: str
    data: dict
    label: str
    pass


class FlowData(BaseModel):
    nodes: List[VFNodeInfo]
    edges: List[VFEdgeInfo]
    pass


class NodeStatus(Enum):
    Pending = "Pending"
    Running = "Running"
    Success = "Success"
    Canceled = "Canceled"
    Error = "Error"
    pass


class NodeWaitType(Enum):
    AND = "AND"
    OR = "OR"
    pass


class NodeType(Enum):
    attached_node_callbackFunc = "attached_node_callbackFunc"
    attached_node_callbackUser = "attached_node_callbackUser"
    attached_node_input = "attached_node_input"
    attached_node_output = "attached_node_output"
    code_interpreter = "code_interpreter"
    cond_branch = "cond_branch"
    detach_run = "detach_run"
    iter_run = "iter_run"
    LLM_inference = "LLM_inference"
    text_input = "text_input"
    text_print = "text_print"
    pass


class VarItem(BaseModel):
    nodeId: str
    nlabel: str
    dpath: List[str]
    dlabel: str
    dkey: str
    dtype: str


class SelectOption(BaseModel):
    label: str
    value: str


class FABaseNode:
    def __init__(self, nodeinfo: VFNodeInfo):
        tmpnodedata = nodeinfo.data
        tmpnodedata.parentNode = nodeinfo.parentNode
        self.nodedata: NodeData = tmpnodedata
        self.nodetype: NodeType = tmpnodedata.ntype
        self.doneEvent = asyncio.Event()
        self.waitEvents: List[asyncio.Event] = []
        self.waitNodes: List["FABaseNode"] = []
        self.status: NodeStatus = NodeStatus.Pending

        self.waitType = NodeWaitType.AND
        pass

    async def _run(self):
        await asyncio.gather(*(event.wait() for event in self.waitEvents))
        waitFunc = all if self.waitType == NodeWaitType.AND else any
        hasError = waitFunc(
            [node.status == NodeStatus.Error for node in self.waitNodes]
        )
        hasCanceled = waitFunc(
            [node.status == NodeStatus.Canceled for node in self.waitNodes]
        )

        # 前置节点出错或取消，本节点取消运行
        if hasError or hasCanceled:
            self.status = NodeStatus.Canceled
            self.doneEvent.set()
            return

        try:
            # 前置节点全部成功，本节点运行
            self.status = NodeStatus.Running
            await self.run()
            self.status = NodeStatus.Success
            pass
        except Exception as e:
            self.status = NodeStatus.Error
            raise e
        finally:
            self.doneEvent.set()
        pass

    async def run(self):
        pass

    def init(self, *args, **kwargs):
        pass

    def fetchSelfConnections(self):
        pass

    def validate(self):
        pass


class FAFlowRunner:
    def __init__(self):
        self.nodes: Dict[str, FABaseNode] = {}
        self.graph = {}
        pass

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
            find_input = list(the_node.nodedata.connections.inputs.keys())
        if find_all_output:
            find_output = list(the_node.nodedata.connections.outputs.keys())

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
            connection = the_node.nodedata.connections.self[hid].data
        elif findtype == "attach":
            connection = the_node.nodedata.connections.attach[hid].data
        elif findtype == "input":
            connection = the_node.nodedata.connections.inputs[hid].data
        elif findtype == "output":
            connection = the_node.nodedata.connections.outputs[hid].data

        for c_data in connection.values():
            if c_data.type == NodeConnectionDataType.FromInner:
                result.append(
                    VarItem(
                        nodeId=nid,
                        nlabel=the_node.nodedata.label,
                        dpath=c_data.path,
                        dlabel=the_node.nodedata.getContent(c_data.path[0])
                        .byId[c_data.path[1]]
                        .label,
                        dkey=the_node.nodedata.getContent(c_data.path[0])
                        .byId[c_data.path[1]]
                        .key,
                        dtype=the_node.nodedata.getContent(c_data.path[0])
                        .byId[c_data.path[1]]
                        .type,
                    )
                )

            elif c_data.type == NodeConnectionDataType.FromOuter:
                # 对于上一个节点，递归搜索上个节点的对应输出handle
                in_hid = c_data.inputKey
                edges = self.get_handle_connections(nid, "target", in_hid)
                print(f"handle id: {in_hid}, edges count: {len(edges)}")

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
                        the_node.nodedata.nesting.attached_nodes[c_data.atype].nid,
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
                        the_node.nodedata.parentNode, False, True, True, [], False, []
                    )
                )

        return result

    async def eval(self, flowdata: FlowData):
        # 初始化所有节点
        for nodeinfo in flowdata.nodes:
            node = FABaseNode(nodeinfo)
            self.nodes[nodeinfo.id] = node
            pass
        # 构建节点连接关系
        for edgeinfo in flowdata.edges:
            if edgeinfo.source in self.nodes and edgeinfo.target in self.nodes:
                source_handle = edgeinfo.sourceHandle
                target_handle = edgeinfo.targetHandle
                if edgeinfo.source not in self.graph:
                    self.graph[edgeinfo.source] = {"source": {}, "target": {}}
                    pass
                if source_handle not in self.graph[edgeinfo.source]:
                    self.graph[edgeinfo.source]["source"][source_handle] = []
                    pass
                self.graph[edgeinfo.source]["source"][source_handle].append(
                    {"nid": edgeinfo.target, "hid": target_handle}
                )
                pass
                if edgeinfo.target not in self.graph:
                    self.graph[edgeinfo.target] = {"source": {}, "target": {}}
                    pass
                if target_handle not in self.graph[edgeinfo.target]:
                    self.graph[edgeinfo.target]["target"][target_handle] = []
                    pass
                self.graph[edgeinfo.target]["target"][target_handle].append(
                    {"nid": edgeinfo.source, "hid": source_handle}
                )
                pass
        for nid in self.nodes.keys():
            node = self.nodes[nid]
            selfVarsList = self.recursive_find_variables(
                nid, True, False, False, [], False, []
            )
            selfVars = [
                {
                    "label": f"{item.nlabel}/{item.dlabel}/{item.dkey}/{item.dtype}",
                    "value": f"{item.nodeId}/{item.dpath[0]}/{item.dpath[1]}",
                }
                for item in selfVarsList
            ]
            print(f"node {nid} selfVars: {selfVars}")
        pass

    def get_handle_connections(self, nid, type, hid):
        if nid in self.graph:
            if type == "source" and hid in self.graph[nid]["source"]:
                return self.graph[nid]["source"][hid]
            elif type == "target" and hid in self.graph[nid]["target"]:
                return self.graph[nid]["target"][hid]
        return None


fr = FAFlowRunner()
with open(
    "test.json",
    "r",
    encoding="utf-8",
) as f:
    flowdata = json.loads(f.read())
    asyncio.run(fr.eval(FlowData.model_validate(flowdata)))
    pass
