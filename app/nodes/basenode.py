from typing import List, Dict, Optional, TYPE_CHECKING, Any
from abc import ABC, abstractmethod
import asyncio
import re
from pydantic import BaseModel
import traceback
import json
import copy
from loguru import logger
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode_contentdata import Single_VarInput, VarType
from app.schemas.vfnode import VFNodeData
from app.schemas.vfnode import VFNodeInfo, VFNodeContentDataType
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
    FAWorkflowNodeResult,
    FAWorkflowResult,
    FAWorkflow,
)
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR


class FABaseNode(ABC):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        cpnodeinfo = copy.deepcopy(nodeinfo)
        self.tid = tid
        self.id = cpnodeinfo.id
        self.oriid = copy.deepcopy(cpnodeinfo.id)
        self.data: VFNodeData = copy.deepcopy(cpnodeinfo.data)
        self.ntype: str = cpnodeinfo.data.ntype
        self.parentNode = cpnodeinfo.parentNode

        # 该节点的输出handle的状态
        self.outputStatus: Dict[str, FANodeStatus] = {
            oname: FANodeStatus.Pending
            for oname in self.data.connections.outputs.keys()
        }
        # 该节点的运行状态
        self.runStatus = FANodeStatus.Pending

        # 该节点需求的验证内容
        self.validateNeededs: List[FANodeValidateNeed] = []
        pass

    def store(self):
        return FAWorkflowNodeResult(
            tid=self.tid,
            id=self.id,
            oriid=self.oriid,
            data=self.data,
            ntype=self.ntype,
            parentNode=self.parentNode,
            runStatus=self.runStatus,
        )

    def restore(self, data: FAWorkflowNodeResult):
        self.tid = data.tid
        self.id = data.id
        self.oriid = data.oriid
        self.data = data.data
        self.ntype = data.ntype
        self.parentNode = data.parentNode
        self.runStatus = data.runStatus
        pass

    @abstractmethod
    async def invoke(self):
        pass

    @abstractmethod
    def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return []

    @abstractmethod
    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        return None
