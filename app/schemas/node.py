import asyncio
import uuid
from typing import List, Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel
import json


class NodeContentData(BaseModel):
    label: str
    type: str
    key: str
    data: Any
    hid: Optional[str] = None
    oid: Optional[str] = None
    pass


class NodeContents(BaseModel):
    byId: Dict[str, NodeContentData]
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
    size: Optional[NodeSize] = None
    min_size: Optional[NodeSize] = None
    attaching: Optional[NodeAttaching] = None
    nesting: Optional[NodeNesting] = None
    connections: Optional[NodeConnections] = None
    payloads: Optional[NodeContents] = None
    results: Optional[NodeContents] = None
    pass

    def get(self, path: List[str]):
        pass

    def getContent(self, content_name: str) -> NodeContents:
        if content_name == "payloads":
            return self.payloads
        elif content_name == "results":
            return self.results


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
