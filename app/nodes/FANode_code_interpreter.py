from typing import List
import asyncio
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData
from app.schemas.farequest import ValidationResult
from .basenode import FABaseNode


class FANode_code_interpreter(FABaseNode):
    def __init__(self, nodeinfo: VFNodeInfo):
        super().__init__(nodeinfo)
        pass

    async def run(self):
        pass

    def init(self, *args, **kwargs):
        pass

    def validateContent(
        self, content_name: str, selfVars: List[str]
    ) -> ValidationResult:
        try:
            for pid in self.data.getContent(content_name).order:
                item: VFNodeContentData = self.data.getContent(content_name).byId[pid]
                for var in item.data:
                    if var["refdata"] not in selfVars:
                        raise Exception("变量出错")
                    pass
        except Exception as e:
            return ValidationResult(isValid=False, message=str(e))
        return ValidationResult(isValid=True, message="")

    def validate(self, selfVars: List[str]) -> ValidationResult:
        return self.validateContent("payloads", selfVars)
