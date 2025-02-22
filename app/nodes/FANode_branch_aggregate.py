from typing import List, Union, Dict, Optional, Any, TYPE_CHECKING
import traceback
import asyncio
import ast
from loguru import logger
from app.schemas.fanode import FARunStatus, FANodeWaitType, FANodeValidateNeed
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
from .tasknode import FATaskNode
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR

if TYPE_CHECKING:
    from app.services.FARunner import FARunner


class FANode_branch_aggregate(FATaskNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
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
            D_BRANCHES: VFNodeContentData = self.data.payloads.byId["D_BRANCHES"]
            for ibranch in D_BRANCHES.data.value:
                branch = Single_AggregateBranch.model_validate(ibranch)
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
                thenode = self.runner().getNode(thiswstatus.nid)
                thisowstatus = thenode.outputStatus[thiswstatus.output]
                if thisowstatus == FARunStatus.Success:
                    preNodeSuccess.add(thiswstatus.nid)
            D_BRANCHES: VFNodeContentData = self.data.payloads.byId["D_BRANCHES"]
            for item in D_BRANCHES.data.value:
                branch = Single_AggregateBranch.model_validate(item)
                nid, ohid = branch.node.split("/")
                if nid in preNodeSuccess:
                    refdata = await self.getRefData(branch.refdata)
                    self.data.results.byId["D_OUTPUT"].data.value = refdata
                    break
            self.setAllOutputStatus(FARunStatus.Success)
            return []

        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"聚合节点运行失败: {errmsg}")
