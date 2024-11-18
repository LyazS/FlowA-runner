from typing import List
import asyncio
from app.schemas.node import NodeData, NodeStatus, NodeWaitType
from app.schemas.vfnode import VFNodeInfo
from app.schemas.validation import ValidationResult
from .basenode import FABaseNode


class FANode_text_print(FABaseNode):
    def __init__(self, nodeinfo: VFNodeInfo):
        pass

    async def run(self):
        pass

    def init(self, *args, **kwargs):
        pass

    def validate(self, selfVars: List[str]) -> ValidationResult:
        return ValidationResult(isValid=True, message="")
