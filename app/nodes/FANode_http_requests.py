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
from app.schemas.vfnode_contentdata import (
    Single_ConditionDict,
    VarType,
    ConditionType,
    Single_VarInput,
)
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
            node_payloads = self.data.getContent("payloads")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            D_CONFIG: VFNodeContentData = node_payloads.byId["D_CONFIG"]
            D_TIMEOUT: VFNodeContentData = node_payloads.byId["D_TIMEOUT"]

            for var_dict in D_VARSINPUT.data:
                var = Single_VarInput.model_validate(var_dict)
                if var.type == "ref" and var.value not in selfVars:
                    error_msgs.append(f"变量未定义{var.value}")
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取results内容失败:{errmsg}")
            logger.error(errmsg)
        finally:
            if len(error_msgs) > 0:
                return ValidationError(nid=self.id, errors=error_msgs)
            return None
    async def run(self) -> List[FANodeUpdateData]:
        try:
            node_payloads = self.data.getContent("payloads")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            D_CONFIG: VFNodeContentData = node_payloads.byId["D_CONFIG"]
            D_TIMEOUT: VFNodeContentData = node_payloads.byId["D_TIMEOUT"]
            D_VARSINPUT_data = D_VARSINPUT.data
            D_CONFIG_data = D_CONFIG.data
            D_TIMEOUT_data = D_TIMEOUT.data

        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"节点运行失败：{errmsg}")
