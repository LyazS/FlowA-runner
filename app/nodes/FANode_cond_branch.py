from typing import List, Union, Dict, Optional, Any, TYPE_CHECKING
import traceback
import asyncio
import ast
from loguru import logger
from app.schemas.fanode import FARunStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import VFNodeInfo
from app.schemas.farequest import ValidationError
from .tasknode import FATaskNode
from app.schemas.fanode import FARunStatus, FANodeWaitType
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
from .tasknode import FATaskNode
from app.services.messageMgr import ALL_MESSAGES_MGR

if TYPE_CHECKING:
    from app.services.FARunner import FARunner


class CompareException(Exception):
    pass


class FANode_cond_branch(FATaskNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
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
                    idata = Single_ConditionDict.model_validate(item.data.value)
                    icondition = idata.conditions
                    for condition in icondition:
                        refdata = condition.refdata
                        if refdata not in selfVars:
                            error_msgs.append(f"变量未定义{refdata}")
                        pass
                        if condition.comparetype == VarType.Ref:
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

    async def run(self) -> List[FANodeUpdateData]:
        try:
            isAnyConditionMet = False
            theresults = self.data.results
            for rid in theresults.order:
                item: VFNodeContentData = theresults.byId[rid]
                if item.type == VFNodeContentDataType.ConditionDict:
                    ikey = item.key
                    if ikey == "cond-else":
                        continue
                    idata = Single_ConditionDict.model_validate(item.data.value)
                    iOutputKey = idata.outputKey
                    icondType = idata.condType
                    icondition = idata.conditions
                    isConditionMet = []
                    for condition in icondition:
                        refdata = await self.getRefData(condition.refdata)
                        if not (
                            condition.operator == "istrue"
                            or condition.operator == "isfalse"
                            or condition.operator == "isnull"
                            or condition.operator == "notnull"
                        ):
                            tmpvarinput = Single_VarInput(
                                key="tmp",
                                type=condition.comparetype,
                                value=condition.value,
                            )
                            comp_refdata = await self.getVar(tmpvarinput)

                        if condition.operator == "eq":
                            isConditionMet.append(refdata == comp_refdata)
                        elif condition.operator == "ne":
                            isConditionMet.append(refdata != comp_refdata)
                        elif condition.operator == "gt":
                            isConditionMet.append(refdata > comp_refdata)
                        elif condition.operator == "lt":
                            isConditionMet.append(refdata < comp_refdata)
                        elif condition.operator == "gte":
                            isConditionMet.append(refdata >= comp_refdata)
                        elif condition.operator == "lte":
                            isConditionMet.append(refdata <= comp_refdata)
                        elif condition.operator == "len_eq":
                            isConditionMet.append(len(refdata) == len(comp_refdata))
                        elif condition.operator == "len_ne":
                            isConditionMet.append(len(refdata) != len(comp_refdata))
                        elif condition.operator == "len_gt":
                            isConditionMet.append(len(refdata) > len(comp_refdata))
                        elif condition.operator == "len_lt":
                            isConditionMet.append(len(refdata) < len(comp_refdata))
                        elif condition.operator == "len_gte":
                            isConditionMet.append(len(refdata) >= len(comp_refdata))
                        elif condition.operator == "len_lte":
                            isConditionMet.append(len(refdata) <= len(comp_refdata))
                        elif condition.operator == "startwith":
                            isConditionMet.append(refdata.startswith(comp_refdata))
                        elif condition.operator == "endwith":
                            isConditionMet.append(refdata.endswith(comp_refdata))
                        elif condition.operator == "contains":
                            isConditionMet.append(comp_refdata in refdata)
                        elif condition.operator == "notcontains":
                            isConditionMet.append(comp_refdata not in refdata)
                        elif condition.operator == "isnull":
                            isConditionMet.append(refdata is None)
                        elif condition.operator == "notnull":
                            isConditionMet.append(refdata is not None)
                        elif condition.operator == "istrue":
                            isConditionMet.append(bool(refdata))
                        elif condition.operator == "isfalse":
                            isConditionMet.append(not bool(refdata))
                        else:
                            raise Exception(f"不支持的比较类型{condition.operator}")
                        pass
                    conditionFunc = all if icondType == ConditionType.AND else any
                    conditionResult = conditionFunc(isConditionMet)
                    if conditionResult:
                        isAnyConditionMet = True
                        self.setAllOutputStatus(FARunStatus.Canceled)
                        self.setOutputStatus(iOutputKey, FARunStatus.Success)
                        break
            if not isAnyConditionMet:
                self.setAllOutputStatus(FARunStatus.Canceled)
                self.setOutputStatus("output-else", FARunStatus.Success)
            return []
        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"节点执行失败：{errmsg}")
        pass
