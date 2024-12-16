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


class CompareException(Exception):
    pass


class FANode_cond_branch(FABaseNode):
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
                    idata = Single_ConditionDict.model_validate(item.data)
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
                            if condition.comparetype == VarType.ref:
                                comp_refdata = await self.getRefData(condition.value)
                            else:
                                comp_refdata = type(refdata)(
                                    ast.literal_eval(condition.value)
                                )

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
                        self.setAllOutputStatus(FANodeStatus.Canceled)
                        self.setOutputStatus(iOutputKey, FANodeStatus.Success)
                        break
            if not isAnyConditionMet:
                self.setAllOutputStatus(FANodeStatus.Canceled)
                self.setOutputStatus("output-else", FANodeStatus.Success)
            return []
        except Exception as e:
            errmsg = traceback.format_exc()
            raise Exception(f"节点执行失败：{errmsg}")
        pass
