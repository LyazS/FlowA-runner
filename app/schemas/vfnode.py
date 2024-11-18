from typing import List, Optional
from pydantic import BaseModel
from .node import NodeData

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


class VFlowData(BaseModel):
    nodes: List[VFNodeInfo]
    edges: List[VFEdgeInfo]
    pass


