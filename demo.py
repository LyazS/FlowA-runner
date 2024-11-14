import asyncio
from typing import List, Union, Any, Dict
from enum import Enum
from pydantic import BaseModel


class NodePayloadsData(BaseModel):
    type: str
    key: str
    data: Any
    hid: Union[str, None]
    oid: Union[str, None]
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
    inputKey: Union[str, None]
    atype: Union[str, None]
    path: Union[List[str], None]
    useid: Union[List[str], None]
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
    self: Union[None, Dict[str, Dict[str, NodeConnection]]]
    attach: Union[None, Dict[str, Dict[str, NodeConnection]]]
    inputs: Union[None, Dict[str, Dict[str, NodeConnection]]]
    outputs: Union[None, Dict[str, Dict[str, NodeConnection]]]
    callbackUsers: Union[None, Dict[str, Dict[str, NodeConnection]]]
    callbackFuncs: Union[None, Dict[str, Dict[str, NodeConnection]]]
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
    width: int
    height: int


class NodeNesting(BaseModel):
    pad: NodePadding
    attached_pad: NodePadding
    attached_nodes: Dict[str, NodeAttachedNode]


class NodeData(BaseModel):
    size: NodeSize
    min_size: NodeSize
    label: str
    placehoderlabel: str
    flags: NodeFlags
    attaching: Union[None, NodeAttaching]
    nesting: Union[None, NodeNesting]
    connections: NodeConnections
    payloads: NodePayloads
    results: NodePayloads
    pass


class NodeInfo(BaseModel):
    ntype: str
    vtype: str
    data: dict


class NodeStatus(Enum):
    Pending = "Pending"
    Running = "Running"
    Success = "Success"
    Canceled = "Canceled"
    Error = "Error"
    pass


class NodeType(Enum):
    pass


class FABaseNode:
    def __init__(self):
        self.nodeinfo: NodeInfo = None
        self.nodetype: NodeType = None
        self.doneEvent = asyncio.Event()
        self.waitEvents = []
        self.waitNodes = []
        self.status = NodeStatus.Pending

    async def run(self):
        await asyncio.gather(*(event.wait() for event in self.waitEvents))

        pass
