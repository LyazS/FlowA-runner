from typing import List, Union, Dict, Optional, Any
import traceback
import asyncio
import ast
from loguru import logger
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError
from .basenode import FABaseNode
from app.schemas.fanode import FANodeStatus, FANodeWaitType
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import Single_ConditionDict, VarType, ConditionType
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
)
from .basenode import FABaseNode
from app.services.messageMgr import ALL_MESSAGES_MGR


class FANode_http_requests(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        pass

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        selfVars = validateVars[FANodeValidateNeed.Self]
        error_msgs = []
        try:
            theresults = self.data.getContent("results")
            for rid in theresults.order:
                item: VFNodeContentData = theresults.byId[rid]
                if item.type == VFNodeContentDataType.ConditionDict:
                    ikey = item.key
                    if ikey == "cond-else":
                        continue
                    idata = Single_ConditionDict.model_validate(item.data)
                    icondition = idata.conditions
                    for condition in icondition:
                        refdata = condition.refdata
                        if refdata not in selfVars:
                            error_msgs.append(f"变量未定义{refdata}")
                        pass
                        if condition.comparetype == VarType.ref:
                            if condition.value not in selfVars:
                                error_msgs.append(f"变量未定义{refdata}")
                            pass
                else:
                    error_msgs.append(f"results内容类型错误{item.type}")
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取results内容失败:{errmsg}")
            logger.error(errmsg)
        finally:
            if len(error_msgs) > 0:
                return ValidationError(nid=self.id, errors=error_msgs)
            return None
