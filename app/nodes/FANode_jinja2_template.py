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
from app.utils.vueRef import serialize_ref, RefOptions, RefTriggerData


class FANode_jinja2_template(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.validateNeededs = [FANodeValidateNeed.Self]
        self.runStatus = FANodeStatus.Passive
        self.inReporting = False
        pass

    async def startReport(self):
        self.inReporting = True
        pass

    async def stopReport(self):
        self.inReporting = False
        pass

    def report(
        self,
        triggerdata: RefTriggerData,
        key,
        tid,
        nid,
        oriid,
    ):
        if not self.inReporting:
            return
        ALL_MESSAGES_MGR.put(
            f"{tid}/Jinja2",
            SSEResponse(
                event=SSEResponseType.updatenode,
                data=SSEResponseData(
                    nid=nid,
                    oriid=oriid,
                    data=[
                        FANodeUpdateData(
                            type=FANodeUpdateType.dontcare,
                            path=[key],
                            data=RefTriggerData(
                                path=triggerdata.path,
                                operation=triggerdata.operation,
                                new_value=serialize_ref(triggerdata.new_value),
                                old_value=serialize_ref(triggerdata.old_value),
                            ),
                        )
                    ],
                ),
            ),
        )
        pass

    async def invoke(self):
        try:
            node_payloads = self.data.getContent("payloads")
            D_VARSINPUT: VFNodeContentData = node_payloads.byId["D_VARSINPUT"]
            for var_dict in D_VARSINPUT.data.value:
                var = Single_VarInput.model_validate(var_dict)
                if var.type == VarType.Ref:
                    refdata: str = var.value
                    nid, contentname, ctid = refdata.split("/")
                    thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid)
                    thenode.data.getContent(contentname).byId[ctid].data.add_dependency(
                        lambda triggerdata, key=var.key, tid=self.tid, nid=self.id, oriid=self.oriid: (
                            self.report(
                                triggerdata,
                                key,
                                tid,
                                nid,
                                oriid,
                            )
                        )
                    )
                    pass

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
            if var.type == VarType.Ref:
                refdata: str = var.value
                nid, contentname, ctid = refdata.split("/")
                thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid)
                curData.append(
                    FANodeUpdateData(
                        type=FANodeUpdateType.dontcare,
                        path=[var.key],
                        data=RefTriggerData(
                            path=[],
                            operation=RefOptions.set,
                            new_value=serialize_ref(
                                thenode.data.getContent(contentname).byId[ctid].data
                            ),
                            old_value=None,
                        ),
                    )
                )
            else:
                curData.append(
                    FANodeUpdateData(
                        type=FANodeUpdateType.dontcare,
                        path=[var.key],
                        data=RefTriggerData(
                            path=[],
                            operation=RefOptions.set,
                            new_value=var.value,
                            old_value=None,
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
                if var.type == VarType.Ref and var.value not in selfVars:
                    error_msgs.append(f"变量未定义{var.value}")
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取内容失败{str(errmsg)}")
        if len(error_msgs) > 0:
            return ValidationError(nid=self.id, errors=error_msgs)
        return None

    @staticmethod
    def getNodeConfig():
        return {}
