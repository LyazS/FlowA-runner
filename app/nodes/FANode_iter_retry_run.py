from typing import List, Dict, Optional, Set, TYPE_CHECKING, Any
import asyncio
import re
from pydantic import BaseModel
import traceback
from loguru import logger
from app.schemas.fanode import FARunStatus, FANodeWaitType, FANodeValidateNeed
from app.schemas.vfnode import (
    VFNodeInfo,
    VFEdgeInfo,
    VFNodeContentDataType,
    VFNodeData,
    VFlowData,
    VFNodeContentData,
    VFNodeFlag,
)
from app.schemas.vfnode_contentdata import (
    Single_VarInput,
    VarType,
    RetryConfigModel,
    RetryInOutModel,
)
from app.schemas.farequest import (
    ValidationError,
    FANodeUpdateType,
    FANodeUpdateData,
    SSEResponse,
    SSEResponseData,
    SSEResponseType,
)
from app.services.messageMgr import ALL_MESSAGES_MGR
from app.services.taskMgr import ALL_TASKS_MGR
from .tasknode import FATaskNode

if TYPE_CHECKING:
    from app.services.FARunner import FARunner


class FANode_iter_retry_run(FATaskNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
        self.validateNeededs = [
            FANodeValidateNeed.Self,
            FANodeValidateNeed.AttachOutput,
        ]
        pass

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        error_msgs = []
        try:
            selfVars = validateVars[FANodeValidateNeed.Self]
            aoutputVars = validateVars[FANodeValidateNeed.AttachOutput]
            node_payloads = self.data.getContent("payloads")
            D_RETRY_INOUT: VFNodeContentData = node_payloads.byId["D_RETRY_INOUT"]
            retry_inout = RetryInOutModel.model_validate(D_RETRY_INOUT.data.value)
            in_ref = retry_inout.input
            if in_ref is None or not isinstance(in_ref, str) or len(in_ref) <= 0:
                error_msgs.append(f"结果{in_ref}没有配置输入选项")
                pass
            elif in_ref not in selfVars:
                error_msgs.append(f"没有该输入选项{in_ref}")
                pass
            out_ref = retry_inout.output
            if out_ref is None or not isinstance(out_ref, str) or len(out_ref) <= 0:
                error_msgs.append(f"结果{out_ref}没有配置输出选项")
                pass
            elif out_ref not in aoutputVars:
                error_msgs.append(f"没有该输出选项{out_ref}")
            pass
        except Exception as e:
            errmsg = traceback.format_exc()
            error_msgs.append(f"获取内容失败{str(errmsg)}")
        finally:
            if len(error_msgs) > 0:
                return ValidationError(nid=self.id, errors=error_msgs)
            return None

    async def run(self) -> List[FANodeUpdateData]:
        from app.nodes.tasknode import FANodeWaitStatus
        from app.nodes import FANODECOLLECTION

        # 获取迭代数组 ===============================================
        nest_layout = self.getNestLayout()
        node_payloads = self.data.getContent("payloads")
        node_results = self.data.getContent("results")

        D_OUTPUT: VFNodeContentData = node_results.byId["D_OUTPUT"]
        D_RETRY_CONFIG: VFNodeContentData = node_payloads.byId["D_RETRY_CONFIG"]
        retry_config = RetryConfigModel.model_validate(D_RETRY_CONFIG.data.value)
        D_RETRY_INOUT: VFNodeContentData = node_payloads.byId["D_RETRY_INOUT"]
        retry_inout = RetryInOutModel.model_validate(D_RETRY_INOUT.data.value)

        node_results = self.data.getContent("results")
        Niter_pattern = r"#(\w+)"

        # 构建子图 ================================================
        flowdata: VFlowData = self.runner().flowdata
        child_node_infos: Dict[str, VFNodeInfo] = {}
        child_edge_infos: Dict[str, VFEdgeInfo] = {}
        # 收集所有子节点
        for nodeinfo in flowdata.nodes:
            if nodeinfo.parentNode == self.oriid and (
                VFNodeFlag.isTask & nodeinfo.data.flag
                or VFNodeFlag.isAttached & nodeinfo.data.flag
            ):
                child_node_infos[nodeinfo.id] = nodeinfo
            pass
        pass
        for edgeinfo in flowdata.edges:
            if (
                edgeinfo.source in child_node_infos
                and edgeinfo.target in child_node_infos
            ):
                child_edge_infos[edgeinfo.id] = edgeinfo
            pass
        # 收集附属节点
        attach_node_name = set(
            [
                "attached_node_input",
                "attached_node_output",
                "attached_node_break",
            ]
        )
        attach_nodeinfo: Dict[str, VFNodeInfo] = {}
        for child_id, child_info in child_node_infos.items():
            if child_info.data.ntype in attach_node_name:
                attach_nodeinfo[child_info.data.ntype] = child_info
                pass
        # 创建input节点
        nodeinfo = attach_nodeinfo["attached_node_input"]
        node_input: FATaskNode = (FANODECOLLECTION[nodeinfo.data.ntype])(
            self.wid,
            nodeinfo,
            self.runner(),
        )
        new_nid = node_input.id.split("#", 1)[0] + "".join(
            map(lambda x: "#" + str(x), nest_layout)
        )
        node_input.setNewID(new_nid)
        self.runner().addNode(node_input.id, node_input)
        # 提前先启动附属节点
        asyncio.create_task(self.runner().getNode(node_input.id).invoke())
        logger.info(f"启动附属节点{'attached_node_input'} {node_input.id}")
        pass

        # 开始迭代重试
        # 迭代项目
        self.iter_item = await self.getRefData(retry_inout.input)
        AddInNodes: List[str] = []
        for iter_idx in range(retry_config.num_retries):
            ChildNodeNames: Set[str] = set()
            # 构建这次重复的输出+next节点
            attached_nodes: Dict[str, FATaskNode] = {}
            for aname in ["attached_node_output", "attached_node_break"]:
                anode: FATaskNode = (
                    FANODECOLLECTION[attach_nodeinfo["attached_node_output"].data.ntype]
                )(
                    self.wid,
                    attach_nodeinfo["attached_node_output"],
                    self.runner(),
                )
                new_nid = anode.id.split("#", 1)[0] + "".join(
                    map(lambda x: "#" + str(x), nest_layout)
                )
                anode.setNewID(new_nid)
                self.runner().addNode(anode.id, anode)
                AddInNodes.append(anode.id)
                attached_nodes[aname] = anode
                pass

            # 构建其余子节点
            child_nodes: Dict[str, FATaskNode] = {}
            for child_id, child_info in child_node_infos.items():
                if child_info.data.ntype in attach_node_name:
                    continue
                child_node: FATaskNode = (FANODECOLLECTION[child_info.data.ntype])(
                    self.wid,
                    child_info,
                    self.runner(),
                )
                new_nid = child_node.id.split("#", 1)[0] + "".join(
                    map(lambda x: "#" + str(x), nest_layout)
                )
                child_node.setNewID(new_nid)
                self.runner().addNode(new_nid, child_node)
                AddInNodes.append(new_nid)
                child_nodes[child_node.id] = child_node
                ChildNodeNames.add(child_node.id)
                pass

            pass
            # 构建节点连接关系
            for edgeinfo in child_edge_infos.values():
                src_node_info = child_node_infos[edgeinfo.source]
                tgt_node_info = child_node_infos[edgeinfo.target]
                if src_node_info.data.ntype == "attached_node_input":
                    src_node = node_input
                    pass
                else:
                    src_nid = edgeinfo.source.split("#", 1)[0] + "".join(
                        map(lambda x: "#" + str(x), nest_layout)
                    )
                    src_node = self.runner().getNode(src_nid)
                if tgt_node_info.data.ntype == "attached_node_output":
                    tgt_node = attached_nodes["attached_node_output"]
                    pass
                elif tgt_node_info.data.ntype == "attached_node_break":
                    tgt_node = attached_nodes["attached_node_break"]
                    pass
                else:
                    tgt_nid = edgeinfo.target.split("#", 1)[0] + "".join(
                        map(lambda x: "#" + str(x), nest_layout)
                    )
                    tgt_node = self.runner().getNode(tgt_nid)
                    pass

                source_handle = edgeinfo.sourceHandle
                target_handle = edgeinfo.targetHandle
                tgt_node.waitEvents.append(src_node.doneEvent)
                tgt_node.waitStatus.append(
                    FANodeWaitStatus(
                        nid=src_node.id,
                        output=source_handle,
                    )
                )
            # 启动子节点
            for nid in child_nodes.keys():
                asyncio.create_task(child_nodes[nid].invoke())
            # 启动output/next附属节点
            task_output = asyncio.create_task(
                attached_nodes["attached_node_output"].invoke()
            )
            task_break = asyncio.create_task(
                attached_nodes["attached_node_break"].invoke()
            )
            await asyncio.wait([task_output, task_break])

            if attached_nodes["attached_node_output"].runStatus == FARunStatus.Success:
                self.iter_item = await self.getRefData(retry_inout.output)
            else:
                logger.error(
                    f"子节点运行失败，迭代{iter_idx+1}/{retry_config.num_retries}"
                )
                for nid in AddInNodes:
                    self.runner().rmNode(nid)
                AddInNodes.clear()
                continue
            if attached_nodes["attached_node_break"].runStatus == FARunStatus.Success:
                self.setAllOutputStatus(FARunStatus.Success)
                D_OUTPUT.data.value = self.iter_item
                return []
            else:
                logger.error(
                    f"子节点运行失败，迭代{iter_idx+1}/{retry_config.num_retries}"
                )
                for nid in AddInNodes:
                    self.runner().rmNode(nid)
                AddInNodes.clear()
                continue

        raise Exception(f"子节点全部运行失败，迭代{retry_config.num_retries}次")
