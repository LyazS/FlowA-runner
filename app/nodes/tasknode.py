from typing import List, Dict, Optional, TYPE_CHECKING, Any
from abc import ABC, abstractmethod
import asyncio
import re
from pydantic import BaseModel
import traceback
import json
import copy
from loguru import logger
from app.schemas.fanode import FARunStatus, FANodeWaitType, FANodeValidateNeed
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
    FAWorkflowNodeRequest,
    FAWorkflowOperationResponse,
)
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR
from app.nodes.basenode import FABaseNode

if TYPE_CHECKING:
    from app.nodes import FANode_iter_run
    from app.services import FARunner


class FANodeWaitStatus(BaseModel):
    nid: str
    output: str
    pass


class NodeCancelException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class FATaskNode(FABaseNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
        # 本节点的完成事件
        self.doneEvent = asyncio.Event()
        # 其他节点的输出handle的状态
        self.waitStatus: List[FANodeWaitStatus] = []
        # 其他节点的doneEvent会存在该节点的waitEvents列表里
        self.waitEvents: List[asyncio.Event] = []
        self.waitType = FANodeWaitType.AND
        pass

    def setNewID(self, newid: str):
        self.id = newid
        pass

    async def startReport(self):
        pass

    async def stopReport(self):
        pass

    async def invoke(self):
        # logger.debug(f"invoke {self.data.label} {self.id}")
        await asyncio.gather(*(event.wait() for event in self.waitEvents))
        # logger.debug(f"wait done {self.data.label} {self.id}")
        try:
            if len(self.waitStatus) > 0:
                # 如果是AND，要求不能出现任何error或cancel状态
                waitFunc = all if self.waitType == FANodeWaitType.AND else any
                preNodeSuccess = []
                for thiswstatus in self.waitStatus:
                    thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(
                        thiswstatus.nid
                    )
                    thisowstatus = thenode.outputStatus[thiswstatus.output]
                    preNodeSuccess.append(thisowstatus == FARunStatus.Success)

                canRunNode = waitFunc(preNodeSuccess)
                # 前置节点出错或取消，本节点取消运行
                if not canRunNode:
                    raise NodeCancelException("前置节点出错或取消，本节点取消运行")
                # logger.debug(f"can run {self.data.label} {self.id}")
            self.setAllOutputStatus(FARunStatus.Running)
            self.putNodeStatus(FARunStatus.Running)

            # 前置节点全部成功，本节点开始运行
            updateDatas = await self.run()
            # 运行成功
            # logger.debug(f"run success {self.data.label} {self.id}")
            # self.setAllOutputStatus(FANodeStatus.Success)
            # 各个输出handle的成功需要由子类函数来设置
            self.putNodeStatus(FARunStatus.Success)
            nodeUpdateDatas = []
            if updateDatas:
                nodeUpdateDatas.extend(updateDatas)
                pass
            ALL_MESSAGES_MGR.put(
                self.tid,
                SSEResponse(
                    event=SSEResponseType.updatenode,
                    data=SSEResponseData(
                        nid=self.id,
                        oriid=self.oriid,
                        data=nodeUpdateDatas,
                    ),
                ),
            )
            pass
        except NodeCancelException as e:
            logger.debug(f"node cancel {self.data.label} {self.id} {e.message}")
            self.setAllOutputStatus(FARunStatus.Canceled)
            self.putNodeStatus(FARunStatus.Canceled)
            pass
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(f"node error {self.data.label} {error_message} {self.id}")
            self.setAllOutputStatus(FARunStatus.Error)
            self.putNodeStatus(FARunStatus.Error)
        finally:
            self.doneEvent.set()
        pass

    def setAllOutputStatus(self, status: FARunStatus):
        for oname in self.outputStatus:
            self.outputStatus[oname] = status
        pass

    def setOutputStatus(self, oname: str, status: FARunStatus):
        self.outputStatus[oname] = status
        pass

    def putNodeStatus(self, status: FARunStatus):
        self.runStatus = status
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
                            path=["state", "status"],
                            data=status,
                        )
                    ],
                ),
            ),
        )
        pass

    async def getRefData(self, refdata: str):
        nid, contentname, ctid = refdata.split("/")
        Niter_pattern = r"#(\w+)"
        nid_matches = re.findall(Niter_pattern, nid)
        nid_layout = len(nid_matches)
        nest_layout = self.getNestLayout()
        if len(nid_matches) > len(nest_layout):
            raise ValueError(f"refdata {refdata} is not valid")
        for i in range(len(nid_matches)):
            nid_matches[i] = nest_layout[i]
        nid_replace = nid.split("#", 1)[0] + "".join(
            map(lambda x: "#" + str(x), nid_matches)
        )
        thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(nid_replace)
        content = thenode.data.getContent(contentname).byId[ctid]
        rtype = content.type
        rdata = None
        # 针对迭代特殊处理
        if rtype == VFNodeContentDataType.IterIndex:
            nest_layout = self.getNestLayout()
            rdata = nest_layout[nid_layout]
            pass
        elif rtype == VFNodeContentDataType.IterItem:
            nest_layout = self.getNestLayout()
            iterNode: "FANode_iter_run" = thenode
            rdata = iterNode.iter_var[nest_layout[nid_layout]]
            pass
        else:
            rdata = content.data.value
        pass
        return rdata

    def getNestLayout(self) -> List[int]:
        pattern = r"#([0-9]+)"
        matches = re.findall(pattern, self.id)
        level = list(map(int, matches))
        return level

    async def getVar(self, var: Single_VarInput):
        if var.type == VarType.String:
            return str(var.value)
        elif var.type == VarType.Number:
            return float(var.value)
        elif var.type == VarType.Boolean:
            return bool(var.value)
        elif var.type == VarType.Integer:
            return int(var.value)
        elif var.type == VarType.Ref:
            return await self.getRefData(var.value)
        pass

    # 需要子类实现的函数 ===============================================================
    # @abstractmethod
    async def run(self) -> List[FANodeUpdateData]:
        self.setAllOutputStatus(FARunStatus.Success)
        pass

    async def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return [
            FANodeUpdateData(
                type=FANodeUpdateType.overwrite,
                path=["state", "status"],
                data=self.runStatus,
            )
        ]

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        return None

    async def processRequest(
        self,
        request: FAWorkflowNodeRequest,
    ) -> Optional[FAWorkflowOperationResponse]:
        return None

    @staticmethod
    def getNodeConfig():
        return {}
