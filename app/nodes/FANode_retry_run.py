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
from app.schemas.vfnode_contentdata import Single_VarInput, VarType, RetryConfigModel
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


class FANode_retry_run(FATaskNode):
    def __init__(self, wid: str, nodeinfo: VFNodeInfo, runner: "FARunner"):
        super().__init__(wid, nodeinfo, runner)
        self.validateNeededs = [
            FANodeValidateNeed.AttachOutput,
        ]
        pass

    def validate(
        self,
        validateVars: Dict[FANodeValidateNeed, Any],
    ) -> Optional[ValidationError]:
        error_msgs = []
        try:
            aoutputVars = validateVars[FANodeValidateNeed.AttachOutput]
            node_results = self.data.getContent("results")
            for rid in node_results.order:
                ref_data = node_results.byId[rid].config.ref
                if (
                    ref_data is None
                    or not isinstance(ref_data, str)
                    or len(ref_data) <= 0
                ):
                    error_msgs.append(f"结果{rid}没有配置输出选项")
                else:
                    if ref_data not in aoutputVars:
                        error_msgs.append(f"没有该输出选项{ref_data}")
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

        D_RETRY_CONFIG: VFNodeContentData = node_payloads.byId["D_RETRY_CONFIG"]
        retry_config = RetryConfigModel.model_validate(D_RETRY_CONFIG.data.value)

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

        # 开始重复
        # 构建结果数组
        node_results_dict = {}
        for rid in node_results.order:
            item: VFNodeContentData = node_results.byId[rid]
            item_ref = item.config.ref
            nidNiter, contentname, ctid = item_ref.split("/")
            nid_matches = re.findall(Niter_pattern, nidNiter)
            if len(nest_layout) != len(nid_matches):
                raise Exception("节点嵌套层数不匹配")
            for level_idx in range(len(nest_layout)):
                nid_matches[level_idx] = nest_layout[level_idx]
                pass
            nid_pattern = nidNiter.split("#", 1)[0] + "".join(
                map(lambda x: "#" + str(x), nid_matches[:-1])
            )
            node_results_dict[rid] = {
                "nid_pattern": nid_pattern,
                "contentname": contentname,
                "ctid": ctid,
            }
        AddInNodes: List[str] = []
        for iter_idx in range(retry_config.num_retries):
            ChildNodeNames: Set[str] = set()
            # 构建这次重复的输出节点
            node_output: FATaskNode = (
                FANODECOLLECTION[attach_nodeinfo["attached_node_output"].data.ntype]
            )(
                self.wid,
                attach_nodeinfo["attached_node_output"],
                self.runner(),
            )
            new_nid = node_output.id.split("#", 1)[0] + "".join(
                map(lambda x: "#" + str(x), nest_layout)
            )
            node_output.setNewID(new_nid)
            self.runner().addNode(node_output.id, node_output)
            AddInNodes.append(node_output.id)

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
                # 真正将结果加入数组
                for rid in node_results_dict.keys():
                    nid_pattern = node_results_dict[rid]["nid_pattern"]
                    if child_node.id.startswith(nid_pattern):
                        contentname = node_results_dict[rid]["contentname"]
                        ctid = node_results_dict[rid]["ctid"]
                        node_results.byId[rid].data = (
                            child_node.data.getContent(contentname).byId[ctid].data
                        )

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
                    tgt_node = node_output
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
            # 启动output附属节点
            task_output = asyncio.create_task(node_output.invoke())
            await task_output
            if node_output.runStatus == FARunStatus.Success:
                self.setAllOutputStatus(FARunStatus.Success)
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
