from typing import List, Union, Dict, Optional, Any
import asyncio
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.farequest import ValidationError
from .basenode import FABaseNode


class FANode_text_print(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        pass

    async def run(self):
        self.setAllOutputStatus(FANodeStatus.Success)
        pass

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        selfVars = validateVars[FANodeValidateNeed.Self]
        error_msgs = []
        try:
            for pid in self.data.getContent("payloads").order:
                item: VFNodeContentData = self.data.getContent("payloads").byId[pid]
                if item.type == VFNodeContentDataType.List:
                    for refdata in item.data.value:
                        if refdata not in selfVars:
                            error_msgs.append(f"变量未定义{refdata}")
                        pass
                else:
                    error_msgs.append(f"payloads内容类型错误{item.type}")
        except Exception as e:
            error_msgs.append(f"获取payloads内容失败:{str(e)}")
        finally:
            if len(error_msgs) > 0:
                return ValidationError(nid=self.id, errors=error_msgs)
            return None
