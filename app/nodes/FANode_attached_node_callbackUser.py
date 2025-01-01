from typing import List, Union, Dict
import asyncio
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError
from .tasknode import FATaskNode


class FANode_attached_node_callbackUser(FATaskNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        pass
