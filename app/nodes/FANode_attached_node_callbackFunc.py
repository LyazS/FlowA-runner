from typing import List, Union, Dict
import asyncio
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError
from .basenode import FABaseNode


class FANode_attached_node_callbackFunc(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        pass

    async def run(self, getNodes: Dict[str, "FABaseNode"]):
        pass

    def init(self, *args, **kwargs):
        pass

    def validate(self, selfVars: List[str]) -> Union[ValidationError, None]:
        return None
