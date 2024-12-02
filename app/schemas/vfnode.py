import asyncio
import uuid
from typing import List, Any, Dict, Optional
from enum import Enum
from pydantic import BaseModel
import json
from .vfnode_contentdata import VFNodeContentDataType, VFNodeContentDataSchema


class VFNodeContentData(BaseModel):
    label: str
    type: VFNodeContentDataType
    key: str
    data: VFNodeContentDataSchema
    hid: Optional[str] = None
    oid: Optional[str] = None
    pass


class VFNodeContents(BaseModel):
    byId: Dict[str, VFNodeContentData]
    order: List[str]
    pass


class VFNodeConnectionDataType(Enum):
    FromOuter = "FromOuter"
    FromAttached = "FromAttached"
    FromParent = "FromParent"
    FromInner = "FromInner"
    pass


class VFNodeConnectionData(BaseModel):
    type: VFNodeConnectionDataType
    inputKey: Optional[str] = None
    atype: Optional[str] = None
    path: Optional[List[str]] = None
    useid: Optional[List[str]] = None
    pass


class VFNodeConnectionType(Enum):
    self = "self"
    attach = "attach"
    inputs = "inputs"
    outputs = "outputs"
    callbackUsers = "callbackUsers"
    callbackFuncs = "callbackFuncs"
    pass


class VFNodeConnection(BaseModel):
    label: str
    data: Dict[str, VFNodeConnectionData]
    pass


class VFNodeConnections(BaseModel):
    self: Optional[Dict[str, VFNodeConnection]] = None
    attach: Optional[Dict[str, VFNodeConnection]] = None
    inputs: Optional[Dict[str, VFNodeConnection]] = None
    outputs: Optional[Dict[str, VFNodeConnection]] = None
    callbackUsers: Optional[Dict[str, VFNodeConnection]] = None
    callbackFuncs: Optional[Dict[str, VFNodeConnection]] = None
    pass


class VFNodeFlags(BaseModel):
    isNested: bool
    isAttached: bool
    isDisabled: bool


class VFNodeAttaching(BaseModel):
    type: str
    pos: str
    label: str
    pass


class VFNodeAttachedNode(BaseModel):
    nid: str
    pass


class VFNodePadding(BaseModel):
    top: int
    bottom: int
    left: int
    right: int
    gap: Optional[int] = None


class VFNodeSize(BaseModel):
    width: float
    height: float


class VFNodeNesting(BaseModel):
    tag: str
    pad: VFNodePadding
    attached_pad: VFNodePadding
    attached_nodes: Dict[str, VFNodeAttachedNode]


class VFNodeData(BaseModel):
    ntype: str
    vtype: str
    flags: VFNodeFlags
    label: str
    placeholderlabel: str
    size: Optional[VFNodeSize] = None
    min_size: Optional[VFNodeSize] = None
    attaching: Optional[VFNodeAttaching] = None
    nesting: Optional[VFNodeNesting] = None
    connections: Optional[VFNodeConnections] = None
    payloads: Optional[VFNodeContents] = None
    results: Optional[VFNodeContents] = None
    pass

    def get(self, path: List[str]):
        pass

    def getContent(self, content_name: str) -> VFNodeContents:
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
    data: VFNodeData
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


class VFlowData(BaseModel):
    nodes: List[VFNodeInfo]
    edges: List[VFEdgeInfo]
    pass
