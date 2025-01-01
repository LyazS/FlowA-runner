from typing import List, Union, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import os
import re
import ast
import copy
import sys
import json
import traceback
import base64
import subprocess
from enum import Enum
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import Single_VarInput, VarType
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
)
from app.utils.tools import read_yaml
from .basenode import FABaseNode
from app.services.messageMgr import ALL_MESSAGES_MGR


class FANode_jinja2_template(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        self.runStatus = FANodeStatus.Passive
        pass

    async def invoke(self):
        node_payloads = self.data.getContent("payloads")
        D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
        for var_dict in D_VARSINPUT.data.value:
            var = Single_VarInput.model_validate(var_dict)
            if var.type == VarType.ref:

                pass
        pass

    def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return []

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        error_msgs = []
        try:
            selfVars = validateVars[FANodeValidateNeed.Self]
            node_payloads = self.data.getContent("payloads")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            for var_dict in D_VARSINPUT.data.value:
                var = Single_VarInput.model_validate(var_dict)
                if var.type == VarType.ref and var.value not in selfVars:
                    error_msgs.append(f"变量未定义{var.value}")
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取内容失败{str(errmsg)}")
        return ValidationError(nid=self.id, errors=error_msgs)
