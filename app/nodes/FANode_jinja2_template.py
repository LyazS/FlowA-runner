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
from loguru import logger
import subprocess
from enum import Enum
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import Single_VarInput, VarType
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
    FAWorkflowNodeRequest,
    FAWorkflowOperationResponse,
)
from app.utils.tools import read_yaml
from .basenode import FABaseNode
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR
from app.utils.vueRef import serialize_ref


class FANode_jinja2_template(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        self.runStatus = FANodeStatus.Passive
        pass

    async def invoke(self):
        try:
            node_payloads = self.data.getContent("payloads")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            for var_dict in D_VARSINPUT.data.value:
                var = Single_VarInput.model_validate(var_dict)
                if var.type == VarType.ref:
                    refdata: str = var.value
                    nid, contentname, ctid = refdata.split("/")
                    thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid)
                    thenode.data.getContent(contentname).byId[ctid].data.add_dependency(
                        lambda path, operation, new_value, old_value, key=var.key, tid=self.tid, nid=self.id, oriid=self.oriid: ALL_MESSAGES_MGR.put(
                            f"{tid}/Jinja2",
                            SSEResponse(
                                event=SSEResponseType.updatenode,
                                data=SSEResponseData(
                                    nid=nid,
                                    oriid=oriid,
                                    data=[
                                        FANodeUpdateData(
                                            type=FANodeUpdateType.overwrite,
                                            path=[key] + path,
                                            data={
                                                "operation": operation,
                                                "new_value": serialize_ref(new_value),
                                                "old_value": old_value,
                                            },
                                        )
                                    ],
                                ),
                            ),
                        )
                    )
                    pass
                else:
                    ALL_MESSAGES_MGR.put(
                        self.tid,
                        SSEResponse(
                            event=SSEResponseType.updatenode,
                            data=SSEResponseData(
                                nid=self.id,
                                oriid=self.oriid,
                                data=[
                                    FANodeUpdateData(
                                        type=FANodeUpdateType.overwrite,
                                        path=var.key,
                                        data=var.value,
                                    )
                                ],
                            ),
                        ),
                    )
        except Exception as e:
            errmsg = traceback.format_exc()
            logger.error(f"执行Jinja2节点{self.id}出错{str(errmsg)}")
            pass
        pass

    async def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        curData = []
        node_payloads = self.data.getContent("payloads")
        D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
        for var_dict in D_VARSINPUT.data.value:
            var = Single_VarInput.model_validate(var_dict)
            if var.type == VarType.ref:
                refdata: str = var.value
                nid, contentname, ctid = refdata.split("/")
                thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid)
                curData.append(
                    FANodeUpdateData(
                        type=FANodeUpdateType.overwrite,
                        path=[var.key],
                        data=serialize_ref(
                            thenode.data.getContent(contentname).byId[ctid].data
                        ),
                    )
                )
        return curData

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
        if len(error_msgs) > 0:
            return ValidationError(nid=self.id, errors=error_msgs)
        return None

    async def processRequest(self, request: dict):
        return FAWorkflowOperationResponse(success=True)
