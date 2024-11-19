from typing import List, Union
import asyncio
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.farequest import ValidationError
from .basenode import FABaseNode


class FANode_code_interpreter(FABaseNode):
    def __init__(self, nodeinfo: VFNodeInfo):
        super().__init__(nodeinfo)
        pass

    async def run(self):
        pass

    def init(self, *args, **kwargs):
        pass

    def validateContent(self, content_name: str, selfVars: List[str]) -> List[str]:
        error_msgs = []
        try:
            for pid in self.data.getContent(content_name).order:
                item: VFNodeContentData = self.data.getContent(content_name).byId[pid]
                if item.type == VFNodeContentDataType.CodeInput:
                    for var in item.data:
                        if var["refdata"] not in selfVars:
                            error_msgs.append(f"变量未定义{var['refdata']}")
                        pass
                elif item.type == VFNodeContentDataType.CodePython:
                    if not isinstance(item.data, str):
                        error_msgs.append(f"Python代码格式错误")
                    pass
                elif item.type == VFNodeContentDataType.CodeJavascipt:
                    if not isinstance(item.data, str):
                        error_msgs.append(f"JavaScript代码格式错误")
                    pass
                else:
                    error_msgs.append(f"类型错误:{item.type}")
            return error_msgs
        except Exception as e:
            error_msgs.append(f"获取{content_name}内容失败:{str(e)}")
            return error_msgs

    def validate(self, selfVars: List[str]) -> ValidationError:
        errors_payloads = self.validateContent("payloads", selfVars)
        if len(errors_payloads) > 0:
            return ValidationError(nid=self.id, errors=errors_payloads)
        return None
