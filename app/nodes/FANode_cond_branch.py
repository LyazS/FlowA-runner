from typing import List
import asyncio
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationResult
from .basenode import FABaseNode


class FANode_cond_branch(FABaseNode):
    def __init__(self, nodeinfo: VFNodeInfo):
        super().__init__(nodeinfo)
        pass

    async def run(self):
        pass

    def init(self, *args, **kwargs):
        pass

    def validate(self, selfVars: List[str]) -> ValidationResult:
        return ValidationResult(isValid=True, message="")
