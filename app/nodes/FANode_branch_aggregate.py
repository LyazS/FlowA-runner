from typing import List, Union, Dict, Optional, Any
import traceback
import asyncio
import ast
from loguru import logger
from app.schemas.fanode import FANodeStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo, VFNodeContentData, VFNodeContentDataType
from app.schemas.vfnode_contentdata import (
    Single_ConditionDict,
    VarType,
    ConditionType,
    Single_AggregateBranch,
)
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
)
from .basenode import FABaseNode
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR


class FANode_branch_aggregate(FABaseNode):
    def __init__(self, tid: str, nodeinfo: VFNodeInfo):
        super().__init__(tid, nodeinfo)
        self.waitType = FANodeWaitType.OR
        self.validateNeededs = [
            FANodeValidateNeed.Self,
            FANodeValidateNeed.InputNodes,
            FANodeValidateNeed.InputNodesWVars,
        ]
        pass

    # 校验节点配置
    # 检查输入节点是否对的上
    # 检查节点的输出变量是否对的上
    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        error_msgs = []
        try:
            InputNodes = validateVars[FANodeValidateNeed.InputNodes]["input"]
            InputNodesWVars = validateVars[FANodeValidateNeed.InputNodesWVars]["input"]
            branches: List[Single_AggregateBranch] = self.data.payloads.byId[
                "D_BRANCHES"
            ].data
            for item in branches:
                branch = Single_AggregateBranch.model_validate(item)
                if branch.node not in InputNodes:
                    error_msgs.append(f"分支节点{branch.node}不在输入节点列表中")
                    pass
                nid, ohid = branch.node.split("/")
                if branch.refdata not in InputNodesWVars[nid][ohid]:
                    error_msgs.append(
                        f"分支节点{branch.node}的输出变量{branch.refdata}不在输入节点{nid}的输出变量列表中"
                    )
                    pass
                pass
            pass
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取payloads内容失败:{errmsg}")
            logger.error(errmsg)
        finally:
            if len(error_msgs) > 0:
                return ValidationError(nid=self.id, errors=error_msgs)
            return None

    async def run(self) -> List[FANodeUpdateData]:
        try:
            preNodeSuccess = set()
            for thiswstatus in self.waitStatus:
                thenode = (await ALL_TASKS_MGR.get(self.tid)).getNode(thiswstatus.nid)
                thisowstatus = thenode.outputStatus[thiswstatus.output]
                if thisowstatus == FANodeStatus.Success:
                    preNodeSuccess.add(thiswstatus.nid)
            branches: List[Single_AggregateBranch] = self.data.payloads.byId[
                "D_BRANCHES"
            ].data
            for item in branches:
                branch = Single_AggregateBranch.model_validate(item)
                nid, ohid = branch.node.split("/")
                if nid in preNodeSuccess:
                    refdata = await self.getRefData(branch.refdata)
                    self.data.results.byId["D_OUTPUT"].data = refdata
                    break
            self.setAllOutputStatus(FANodeStatus.Success)
            return [
                FANodeUpdateData(
                    type=FANodeUpdateType.overwrite,
                    path=["results", "byId", "D_OUTPUT", "data"],
                    data=self.data.results.byId["D_OUTPUT"].data,
                )
            ]

        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"聚合节点运行失败: {errmsg}")

    def getCurData(self) -> Optional[List[FANodeUpdateData]]:
        return [
            FANodeUpdateData(
                type=FANodeUpdateType.overwrite,
                path=["state", "status"],
                data=self.runStatus,
            )
        ] + [
            FANodeUpdateData(
                type=FANodeUpdateType.overwrite,
                path=["results", "byId", "D_OUTPUT", "data"],
                data=self.data.results.byId["D_OUTPUT"].data,
            )
        ]
